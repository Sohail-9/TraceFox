from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import Counter, OrderedDict
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from services.integrations.github_publisher import publisher
from services.query.service import QueryOrchestrationService
from services.review_engine.router import ModelRouter
from services.scoring.service import ConfidenceScoringService
from services.shared.event_bus import event_bus
from services.shared.llm_clients import LlamaClient
from services.shared.llm_utils import call_chat_completion, extract_token_usage, calculate_cost
from services.shared.models import (
    AnalysisStatus,
    FilePayload,
    Finding,
    FindingCategory,
    FindingPriority,
    FindingSeverity,
    FindingSource,
    ReviewSummary,
    WebhookPayload,
)

logger = logging.getLogger(__name__)


class PRAnalysisEngine:
    """Implements multi-pass PR analysis orchestrating Llama + DeepSeek models."""

    def __init__(
        self,
        *,
        quick_filter_client: Optional[LlamaClient] = None,
        llama_client: Optional[LlamaClient] = None,
        deepseek_call: Optional[Callable[..., Dict[str, Any]]] = None,
        deepseek_model: str = "deepseek-r1",
        scoring: Optional[ConfidenceScoringService] = None,
        query_service: Optional[QueryOrchestrationService] = None,
    ) -> None:
        self.quick_filter_client = quick_filter_client or LlamaClient(model_name="llama3-8b")
        self.security_client = llama_client or LlamaClient(model_name="llama2")
        self.deepseek_call = deepseek_call or call_chat_completion
        self.deepseek_model = deepseek_model
        self.scoring = scoring or ConfidenceScoringService()
        self.query = query_service or QueryOrchestrationService()
        self._reviews: Dict[str, ReviewSummary] = {}
        self._lock = asyncio.Lock()
        self.router = ModelRouter()
        self._response_cache: OrderedDict[str, Any] = OrderedDict()
        self._max_cache_entries = 128

    async def run_review(self, pr_id: str, payload: WebhookPayload) -> ReviewSummary:
        async with self._lock:
            start_time = time.perf_counter()
            diff = self._compose_diff(payload)
            context = self._build_context(payload)
            quick_filter = await asyncio.to_thread(self._quick_filter, diff)
            routing_snapshot = {
                "quick_filter": self.router.route_analysis("quick_filter"),
                "security": self.router.route_analysis("security"),
                "breaking_changes": self.router.route_analysis("breaking_changes"),
                "cross_layer": self.router.route_analysis("cross_layer"),
            }
            metadata = {"quick_filter": quick_filter, "context": context, "routing": routing_snapshot}

            if not quick_filter.get("has_issues", True):
                logger.info("Quick filter suppressed analysis for %s: %s", pr_id, quick_filter.get("reason"))
                review = self._finalise_review(
                    pr_id,
                    payload,
                    [],
                    metadata,
                    start_time,
                    summary_override=f"No significant issues detected. {quick_filter.get('reason', '').strip()}",
                )
                self._reviews[pr_id] = review
                await event_bus.publish(
                    "review:completed",
                    {"pr_id": pr_id, "review_id": review.review_id, "total_findings": review.total_findings},
                )
                self._publish_to_github(review, payload)
                return review

            tasks = [
                asyncio.to_thread(self._analyze_security_and_style, diff),
                asyncio.to_thread(self._analyze_complex_logic, diff, context),
                asyncio.to_thread(self._analyze_cross_file_impact, payload.files),
            ]
            chunks = await asyncio.gather(*tasks, return_exceptions=True)
            findings: List[Finding] = []
            for chunk in chunks:
                if isinstance(chunk, Exception):
                    logger.error("Analysis chunk failed for PR %s: %s", pr_id, chunk)
                    continue
                findings.extend(chunk)

            scored = self._score_findings(findings)
            scored = [
                f
                for f in scored
                if (str(f.classification).upper() if f.classification else "") != FindingPriority.suppressed.value
            ]
            review = self._finalise_review(pr_id, payload, scored, metadata, start_time)
            self._reviews[pr_id] = review
            await event_bus.publish(
                "review:completed",
                {"pr_id": pr_id, "review_id": review.review_id, "total_findings": review.total_findings},
            )
            self._publish_to_github(review, payload)
            return review

    async def get_review(self, pr_id: str) -> Optional[ReviewSummary]:
        return self._reviews.get(pr_id)

    async def all_reviews(self) -> List[ReviewSummary]:
        async with self._lock:
            return list(self._reviews.values())

    # ---------- analysis stages ----------

    def _quick_filter(self, diff: str) -> Dict[str, Any]:
        prompt = (
            "Quickly scan this diff and identify if there are ANY significant issues:\n"
            f"{diff}\n"
            'Respond with JSON {"has_issues": true|false, "reason": "brief explanation"}'
        )
        result = self._cached_result(
            "quick-filter",
            diff,
            lambda: self.quick_filter_client.generate(prompt, max_tokens=256),
        )
        if result["status"] != "success":
            return {"has_issues": True, "reason": "LLM default - unable to interpret diff"}
        try:
            parsed = json.loads(result["response"])
            return {
                "has_issues": bool(parsed.get("has_issues", True)),
                "reason": str(parsed.get("reason") or "analysis requested"),
            }
        except json.JSONDecodeError:
            return {"has_issues": True, "reason": "LLM parsing fallback"}

    def _analyze_security_and_style(self, diff: str) -> List[Finding]:
        prompt = (
            "Analyze this code diff for security issues and style violations:\n"
            f"{diff}\n"
            "Identify security vulnerabilities, code style violations, and anti-patterns.\n"
            "Return JSON array with findings keyed as "
            "['id','file_path','line_number','severity','type','message','suggested_fix','impact','confidence']."
        )
        response = self._cached_result(
            "security-style",
            diff,
            lambda: self.security_client.generate(prompt, max_tokens=1024, temperature=0.2),
        )
        if response["status"] != "success":
            return []
        return self._parse_llm_findings(response["response"], FindingSource.llama)

    def _analyze_complex_logic(self, diff: str, context: Dict[str, Any]) -> List[Finding]:
        payload = {
            "diff": diff,
            "context": context,
            "instructions": [
                "Identify breaking changes, cross-layer inconsistencies, and performance regressions.",
                "Highlight logic errors with concrete caller/callee impacts.",
            ],
        }
        context_blob = json.dumps(context, sort_keys=True)
        response = self._cached_result(
            "deepseek-breaking",
            f"{diff}:{context_blob}",
            lambda: self.deepseek_call(
                model=self.deepseek_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a code review expert specialising in breaking changes, cross-layer impacts, "
                            "and performance regressions. Respond with JSON describing findings."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
                max_tokens=2048,
                temperature=0.1,
                top_p=0.9,
                stream=False,
            ),
        )
        choices = (response or {}).get("choices") or []
        if not choices:
            logger.warning("DeepSeek response missing choices payload: %s", response)
            return []
        message = choices[0].get("message", {})
        content = message.get("content", "")
        prompt_tokens, completion_tokens = extract_token_usage(response)
        if prompt_tokens or completion_tokens:
            cost = calculate_cost(self.deepseek_model, prompt_tokens, completion_tokens)
            logger.debug(
                "DeepSeek usage prompt=%s completion=%s cost=$%.6f", prompt_tokens, completion_tokens, cost
            )
        return self._parse_llm_findings(content, FindingSource.deepseek)

    def _analyze_cross_file_impact(self, files: List[FilePayload]) -> List[Finding]:
        findings: List[Finding] = []
        for file in files:
            callers = self.query.callers_for_file(file.path)
            dependencies = self.query.dependencies_for_file(file.path)
            if callers:
                metadata = {"affected_components": len(callers), "corroborating_signals": 1, "dependency_depth": 1}
                findings.append(
                    Finding(
                        id=str(uuid4()),
                        type=FindingCategory.cross_layer,
                        severity=FindingSeverity.medium,
                        confidence=0.55,
                        message=f"File has {len(callers)} upstream callers that may require updates.",
                        file_path=file.path,
                        line_number=0,
                        impact="Upstream functions depend on this file.",
                        source_model=FindingSource.graph,
                        metadata=metadata,
                    )
                )
            if dependencies:
                metadata = {
                    "affected_components": len(dependencies),
                    "dependency_depth": len(dependencies),
                    "corroborating_signals": 2,
                }
                findings.append(
                    Finding(
                        id=str(uuid4()),
                        type=FindingCategory.breaking_change,
                        severity=FindingSeverity.medium,
                        confidence=0.6,
                        message=f"Changes may impact dependent modules: {', '.join(dependencies)}",
                        file_path=file.path,
                        line_number=0,
                        impact="Downstream dependencies detected in graph traversal.",
                        source_model=FindingSource.graph,
                        metadata=metadata,
                    )
                )
        return findings

    # ---------- helpers ----------

    def _parse_llm_findings(self, content: str, source: FindingSource) -> List[Finding]:
        structured = self._safe_load_json(content)
        if isinstance(structured, dict):
            payload = structured.get("findings", [])
        else:
            payload = structured
        if not isinstance(payload, list):
            payload = []

        findings: List[Finding] = []
        for item in payload:
            try:
                findings.append(
                    Finding(
                        id=str(item.get("id") or uuid4()),
                        type=self._normalise_category(item.get("type") or item.get("category")),
                        severity=self._normalise_severity(item.get("severity")),
                        confidence=float(item.get("confidence") or item.get("confidence_score") or 0.5),
                        message=str(item.get("message") or item.get("description") or "Unspecified issue."),
                        file_path=str(item.get("file_path") or "unknown.py"),
                        line_number=int(item.get("line_number") or 0),
                        suggested_fix=item.get("suggested_fix"),
                        impact=item.get("impact"),
                        source_model=source,
                        metadata={
                            "context_overlap": float(item.get("context_relevance") or 0.5),
                            "affected_components": len(item.get("related_files") or []) or 1,
                            "dependency_depth": int(item.get("dependency_depth") or 1),
                            "corroborating_signals": len(item.get("signals") or []),
                        },
                        remediation=item.get("recommendations"),
                        code_diff=item.get("code_diff"),
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive parsing
                logger.debug("Skipping invalid finding payload %s: %s", item, exc)
        return findings

    def _safe_load_json(self, content: str) -> Any:
        content = (content or "").strip()
        if not content:
            return []
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    logger.debug("Unable to parse JSON from response: %s", content[:200])
        return []

    def _normalise_category(self, raw: Any) -> FindingCategory:
        value = str(raw or "").lower()
        mapping = {
            "bug": FindingCategory.logic,
            "test_gap": FindingCategory.logic,
            "cross-layer": FindingCategory.cross_layer,
            "cross_layer": FindingCategory.cross_layer,
        }
        for category in FindingCategory:
            if value in {category.value, category.name.lower()}:
                return category
        return mapping.get(value, FindingCategory.logic)

    def _normalise_severity(self, raw: Any) -> FindingSeverity:
        value = str(raw or "medium").lower()
        legacy = {"critical": FindingSeverity.high, "major": FindingSeverity.medium, "minor": FindingSeverity.low}
        if value in {"high", "sev1"}:
            return FindingSeverity.high
        if value in {"medium", "sev2"}:
            return FindingSeverity.medium
        if value in {"low", "sev3"}:
            return FindingSeverity.low
        return legacy.get(value, FindingSeverity.medium)

    def _compose_diff(self, payload: WebhookPayload) -> str:
        snippets: List[str] = []
        for file in payload.files[:10]:
            snippet = file.content[:1_500]
            snippets.append(f"File: {file.path}\nLanguage: {file.language}\n```diff\n{snippet}\n```")
        return "\n\n".join(snippets) if snippets else "No diff available."

    def _build_context(self, payload: WebhookPayload) -> Dict[str, Any]:
        files = [file.path for file in payload.files]
        languages = sorted({file.language for file in payload.files})
        return {
            "files": files,
            "languages": languages,
            "author": payload.pull_request.author,
            "title": payload.pull_request.title,
            "repository": payload.repository.name,
        }

    def _score_findings(self, findings: List[Finding]) -> List[Finding]:
        scored: List[Finding] = []
        for finding in findings:
            payload = finding.model_dump()
            confidence = self.scoring.calculate_confidence(finding)
            classification = self.scoring.classify_severity(confidence)
            payload["confidence"] = confidence
            payload["classification"] = classification.value if isinstance(classification, FindingPriority) else classification
            scored.append(Finding(**payload))
        return scored

    def _build_summary_text(self, findings: List[Finding]) -> str:
        if not findings:
            return "No actionable issues detected across quick filter, Llama, or DeepSeek stages."
        by_category = Counter(f.type for f in findings)
        top_categories = ", ".join(f"{cat.value}:{count}" for cat, count in by_category.most_common())
        priorities = Counter(f.classification for f in findings if f.classification)
        priority_summary = ", ".join(f"{key}:{value}" for key, value in priorities.items())
        return f"Identified {len(findings)} findings ({top_categories}). Priority mix: {priority_summary or 'balanced'}."

    def _resolve_primary_model(self, findings: List[Finding]) -> str:
        if any(f.source_model == FindingSource.deepseek for f in findings):
            return "deepseek-coder-67b"
        return "llama3"

    def _finalise_review(
        self,
        pr_id: str,
        payload: WebhookPayload,
        findings: List[Finding],
        metadata: Dict[str, Any],
        start_time: float,
        *,
        summary_override: Optional[str] = None,
    ) -> ReviewSummary:
        total = len(findings)
        classifications = Counter(f.classification for f in findings if f.classification)
        review = ReviewSummary(
            review_id=str(uuid4()),
            pr_id=pr_id,
            repository=payload.repository.name,
            pr_number=payload.pull_request.number,
            summary=summary_override or self._build_summary_text(findings),
            findings=findings,
            total_findings=total,
            must_fix_count=int(classifications.get(FindingPriority.must_fix.value, 0)),
            should_fix_count=int(classifications.get(FindingPriority.should_fix.value, 0)),
            nice_to_fix_count=int(classifications.get(FindingPriority.nice_to_fix.value, 0)),
            primary_model=self._resolve_primary_model(findings),
            duration_ms=int((time.perf_counter() - start_time) * 1000),
            analysis_status=AnalysisStatus.completed,
            metadata=metadata,
        )
        return review

    def _publish_to_github(self, review: ReviewSummary, payload: WebhookPayload) -> None:
        logger.info("Generated review %s for PR %s", review.review_id, review.pr_id)
        try:
            repo_url = str(payload.repository.url)
            pr_number = int(payload.pull_request.number)
            publisher.publish(
                repo_url=repo_url,
                pr_number=pr_number,
                head_sha=None,
                findings=review.findings,
                summary_text=review.summary,
            )
        except Exception as exc:  # pragma: no cover - publishing best-effort
            logger.warning("GitHub publish skipped: %s", exc)

    def _cached_result(self, stage: str, payload: str, compute: Callable[[], Any]) -> Any:
        cache_key = self._cache_key(stage, payload)
        if cache_key in self._response_cache:
            self._response_cache.move_to_end(cache_key)
            return self._response_cache[cache_key]
        result = compute()
        self._response_cache[cache_key] = result
        if len(self._response_cache) > self._max_cache_entries:
            self._response_cache.popitem(last=False)
        return result

    def _cache_key(self, stage: str, payload: str) -> str:
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
        return f"{stage}:{digest}"


# Convenience shim for backwards compatibility
AIReviewEngine = PRAnalysisEngine

__all__ = ["PRAnalysisEngine", "AIReviewEngine"]
