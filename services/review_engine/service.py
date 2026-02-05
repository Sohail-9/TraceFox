from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import Counter, OrderedDict
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from services.shared.cache import cache

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

    async def run_review(
        self,
        pr_id: str,
        payload: WebhookPayload,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> ReviewSummary:
        async with self._lock:
            # Check if review already exists
            if pr_id in self._reviews:
                return self._reviews[pr_id]

            start_time = time.perf_counter()

            if progress_callback:
                await progress_callback("⏳ Initializing analysis...")

            # 1. Prepare data
            diff = self._compose_diff(payload)
            context = self._build_context(payload)
            quick_filter = await self._quick_filter(diff)
            routing_snapshot = {
                "quick_filter": self.router.route_analysis("quick_filter"),
                "security": self.router.route_analysis("security"),
                "logic": self.router.route_analysis("logic"),
            }
            
            # 2. Quick Filter
            if not quick_filter.get("has_issues", False):
                logger.info("Quick filter suppressed analysis for %s: %s", pr_id, quick_filter.get("reason"))
                if progress_callback:
                    await progress_callback("✅ No significant issues found during quick scan.")
                review = ReviewSummary(
                    review_id=str(uuid4()),
                    pr_id=pr_id,
                    repository=payload.repository.name,
                    pr_number=payload.pull_request.number,
                    status=AnalysisStatus.completed,
                    findings=[],
                    summary=f"No significant issues detected. {quick_filter.get('reason', '').strip()}",
                    model_used="quick_filter",
                    routing_info=routing_snapshot,
                    processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                    total_findings=0,
                    metadata={"quick_filter": quick_filter, "context": context},
                )
                self._reviews[pr_id] = review
                await event_bus.publish(
                    "review:completed",
                    {"pr_id": pr_id, "review_id": review.review_id, "total_findings": review.total_findings},
                )
                await self._publish_to_github(review, payload)
                return review

            if progress_callback:
                await progress_callback("🛡️ Analyzing security and style...")
            
            security_findings = await self._analyze_security_and_style(diff)
            
            if progress_callback:
                await progress_callback("🧠 Analyzing complex logic and architecture...")
            
            logic_findings = await self._analyze_complex_logic(diff, context)
            
            if progress_callback:
                await progress_callback("🚀 Analyzing performance impact...")
            
            perf_findings = await self._analyze_performance(diff)
            
            if progress_callback:
                await progress_callback("🕸️ Analyzing cross-file dependencies...")
                
            impact_findings = await asyncio.to_thread(self._analyze_cross_file_impact, payload.files)

            all_findings: List[Finding] = []
            all_findings.extend(security_findings)
            all_findings.extend(logic_findings)
            all_findings.extend(perf_findings)
            all_findings.extend(impact_findings)

            scored = self._score_findings(all_findings)
            scored = [
                f
                for f in scored
                if (str(f.classification).upper() if f.classification else "") != FindingPriority.suppressed.value
            ]
            
            if progress_callback:
                await progress_callback("✅ Analysis complete. Generating report...")
            
            review = ReviewSummary(
                review_id=str(uuid4()),
                pr_id=pr_id,
                repository=payload.repository.name,
                pr_number=payload.pull_request.number,
                status=AnalysisStatus.completed,
                findings=scored,
                summary=self._build_summary_text(scored),
                model_used=self._resolve_primary_model(scored),
                routing_info=routing_snapshot,
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                total_findings=len(scored),
                metadata={"quick_filter": quick_filter, "context": context},
            )
            
            self._reviews[pr_id] = review
            await event_bus.publish(
                "review:completed",
                {"pr_id": pr_id, "review_id": review.review_id, "total_findings": review.total_findings},
            )
            await self._publish_to_github(review, payload)
            return review

    async def handle_conversation(
        self,
        pr_id: str,
        question: str,
        finding_id: Optional[str] = None,
    ) -> str:
        """Process a user question about a finding or the PR and return a response."""
        review = await self.get_review(pr_id)
        context_finding = None
        if review and finding_id:
            context_finding = next((f for f in review.findings if f.id == finding_id), None)

        system_prompt = (
            "You are TraceFox, a world-class code reviewer and architectural assistant. "
            "A developer is asking you a question about your previous review findings. "
            "Be helpful, concise, and provide code examples if applicable."
        )
        
        user_prompt = f"Question: {question}\n\n"
        if context_finding:
            user_prompt += (
                f"Context Finding:\n"
                f"- File: {context_finding.file_path}\n"
                f"- Line: {context_finding.line_number}\n"
                f"- Issue: {context_finding.message}\n"
                f"- Suggestion: {context_finding.suggested_fix}\n"
            )
        elif review:
            user_prompt += f"Context: This is about PR #{review.pr_number} in {review.repository}."

        # Pass specific keyword arguments to match call_chat_completion signature
        response = await asyncio.to_thread(
            self.deepseek_call,
            model=self.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1024,
            temperature=0.3
        )
        
        choices = (response or {}).get("choices") or []
        if not choices:
            return "I'm sorry, I'm having trouble processing that request right now."
        
        return choices[0].get("message", {}).get("content", "I don't have an answer for that yet.")

    async def get_review(self, pr_id: str) -> Optional[ReviewSummary]:
        return self._reviews.get(pr_id)

    async def all_reviews(self) -> List[ReviewSummary]:
        async with self._lock:
            return list(self._reviews.values())

    # ---------- analysis stages ----------

    async def _quick_filter(self, diff: str) -> Dict[str, Any]:
        prompt = (
            "Quickly scan this diff and identify if there are ANY significant issues:\n"
            f"{diff}\n"
            'Respond with JSON {"has_issues": true|false, "reason": "brief explanation"}'
        )
        result = await self._cached_result(
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

    async def _analyze_security_and_style(self, diff: str) -> List[Finding]:
        prompt = (
            "You are a world-class code reviewer. Analyze this code diff for security issues and style violations.\n\n"
            "Diff:\n"
            f"{diff}\n\n"
            "Instructions:\n"
            "1. Identify security vulnerabilities (SQL injection, XSS, hardcoded secrets, etc.).\n"
            "2. Identify style violations and anti-patterns (naming, complexity, dry principle, etc.).\n"
            "3. Provide actionable feedback with specific line numbers.\n"
            "4. For any fix, provide a 'suggested_fix' using exact code that should replace the current line(s).\n\n"
            "Return a JSON array of findings with these keys: "
            "['id','file_path','line_number','severity','type','message','suggested_fix','impact','confidence']."
        )
        response = await self._cached_result(
            "security-style",
            diff,
            lambda: self.security_client.generate(prompt, max_tokens=1024, temperature=0.2),
        )
        if response["status"] != "success":
            return []
        return self._parse_llm_findings(response["response"], FindingSource.llama)

    async def _analyze_complex_logic(self, diff: str, context: Dict[str, Any]) -> List[Finding]:
        payload = {
            "diff": diff,
            "context": context,
            "instructions": [
                "Identify breaking changes, cross-layer inconsistencies, and performance regressions.",
                "Highlight logic errors with concrete caller/callee impacts.",
            ],
        }
        context_blob = json.dumps(context, sort_keys=True)
        response = await self._cached_result(
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

    async def _analyze_performance(self, diff: str) -> List[Finding]:
        prompt = (
            "You are a performance optimization expert. Analyze this code diff for potential performance regressions or optimizations:\n\n"
            "Diff:\n"
            f"{diff}\n\n"
            "Instructions:\n"
            "1. Look for N+1 query problems, inefficient loops, or large memory allocations.\n"
            "2. Identify missing indices or inefficient data structures.\n"
            "3. Suggest concrete improvements with code examples.\n"
            "Return a JSON array of findings keyed as "
            "['id','file_path','line_number','severity','type','message','suggested_fix','impact','confidence']."
        )
        response = await self._cached_result(
            "performance-analysis",
            diff,
            lambda: self.security_client.generate(prompt, max_tokens=1024, temperature=0.1),
        )
        if response["status"] != "success":
            return []
        return self._parse_llm_findings(response["response"], FindingSource.llama)

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

    def _generate_mermaid_chart(self, findings: List[Finding]) -> str:
        """Generate a Mermaid.js dependency graph from cross-layer findings."""
        edges = set()
        for f in findings:
            if f.type == FindingCategory.cross_layer and f.metadata:
                source = f.file_path.split("/")[-1]
                # We assume metadata contains dependency info or we extract from message
                # For now, let's look for known patterns or just map file -> finding type
                edges.add(f'{source} -->|"Impacts"| Unknown(("Dependent Components"))')
                
                # Ideally, finding metadata should have 'affected_files' list
                affected = f.metadata.get("affected_files", [])
                for target in affected:
                     target_name = target.split("/")[-1]
                     edges.add(f'{source} -->|"{f.impact or "Calls"}"| {target_name}')

        if not edges:
            return ""

        chart = ["```mermaid", "graph TD"]
        chart.extend(f"    {edge}" for edge in sorted(edges))
        chart.append("```")
        return "\n".join(chart)

    def _build_summary_text(self, findings: List[Finding]) -> str:
        if not findings:
            return "### TraceFox Review: No issues detected\n\nI've analyzed your changes and found no significant issues. Great job!"
        
        by_category = Counter(f.type for f in findings)
        by_severity = Counter(f.severity for f in findings)
        
        summary_lines = [
            "### TraceFox Review Summary",
            f"I've identified **{len(findings)}** actionable findings across your PR.",
            "",
            "#### Breakdown by Severity",
            f"- 🔴 **High**: {by_severity.get(FindingSeverity.high, 0)}",
            f"- 🟡 **Medium**: {by_severity.get(FindingSeverity.medium, 0)}",
            f"- 🟢 **Low**: {by_severity.get(FindingSeverity.low, 0)}",
            "",
            "#### Breakdown by Category"
        ]
        
        for cat, count in by_category.most_common():
            label = str(cat.value).replace('_', ' ').title()
            summary_lines.append(f"- **{label}**: {count}")
            
        # Add Mermaid Chart if applicable
        mermaid_chart = self._generate_mermaid_chart(findings)
        if mermaid_chart:
            summary_lines.append("")
            summary_lines.append("#### 🕸️ Dependency Impact Analysis")
            summary_lines.append(mermaid_chart)
            
        summary_lines.append("")
        summary_lines.append("> [!TIP]")
        summary_lines.append("> You can apply suggested fixes directly from the comments below.")
        
        return "\n".join(summary_lines)

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

    async def _publish_to_github(self, review: ReviewSummary, payload: WebhookPayload) -> None:
        logger.info("Generated review %s for PR %s", review.review_id, review.pr_id)
        try:
            repo_url = str(payload.repository.url)
            pr_number = int(payload.pull_request.number)
            await publisher.publish(
                repo_url=repo_url,
                pr_number=pr_number,
                head_sha=None,
                findings=review.findings,
                summary_text=review.summary,
            )
        except Exception as exc:  # pragma: no cover - publishing best-effort
            logger.warning("GitHub publish skipped: %s", exc)

    async def _cached_result(self, stage: str, payload: str, compute: Callable[..., Any]) -> Any:
        cache_key = ["review", "engine", stage, hashlib.sha1(payload.encode("utf-8")).hexdigest()]
        cached = await cache.get_json(cache_key)
        if cached is not None:
            return cached
        
        # If compute is a coroutine, await it, otherwise run it in a thread if it's blocking
        if asyncio.iscoroutinefunction(compute):
            result = await compute()
        else:
            result = compute()
            
        await cache.set_json(cache_key, result, ttl=3600)  # 1 hour cache
        return result


# Convenience shim for backwards compatibility
AIReviewEngine = PRAnalysisEngine

__all__ = ["PRAnalysisEngine", "AIReviewEngine"]
