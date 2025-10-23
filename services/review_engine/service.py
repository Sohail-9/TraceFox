from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from services.shared.event_bus import event_bus
from services.shared.llm_utils import call_chat_completion
from services.shared.models import (
    FindingCategory,
    ReviewFinding,
    ReviewSummary,
    Severity,
    WebhookPayload,
)
from services.integrations.github_publisher import publisher

logger = logging.getLogger(__name__)


class AIReviewEngine:
    """Coordinates AI models and static analysis to produce review findings."""

    def __init__(self) -> None:
        self._reviews: Dict[str, ReviewSummary] = {}
        self._lock = asyncio.Lock()
        self._analysis_model = "DeepSeek-R1"

    async def run_review(self, pr_id: str, payload: WebhookPayload) -> ReviewSummary:
        async with self._lock:
            review_data = await self._invoke_analysis_model(pr_id, payload)
            findings = review_data.get("findings", [])
            review_summary = ReviewSummary(
                review_id=str(uuid4()),
                pr_id=pr_id,
                summary=review_data.get("summary", "No issues detected."),
                findings=findings,
                total_findings=len(findings),
                critical_count=sum(1 for f in findings if f.severity == Severity.critical),
                major_count=sum(1 for f in findings if f.severity == Severity.major),
                minor_count=sum(1 for f in findings if f.severity == Severity.minor),
            )
            self._reviews[pr_id] = review_summary
            await event_bus.publish(
                "review:completed",
                {"pr_id": pr_id, "review_id": review_summary.review_id, "total_findings": len(findings)},
            )
            logger.info("Generated review %s for PR %s", review_summary.review_id, pr_id)

            # Best-effort GitHub publish (no-op if disabled)
            try:
                repo_url = str(payload.repository.url)
                pr_number = int(payload.pull_request.number)
                publisher.publish(
                    repo_url=repo_url,
                    pr_number=pr_number,
                    head_sha=None,  # Could be fetched via API when credentials are present
                    findings=findings,
                    summary_text=review_summary.summary,
                )
            except Exception as exc:  # pragma: no cover - should never block
                logger.warning("GitHub publish skipped: %s", exc)
            return review_summary

    async def get_review(self, pr_id: str) -> Optional[ReviewSummary]:
        return self._reviews.get(pr_id)

    async def all_reviews(self) -> List[ReviewSummary]:
        async with self._lock:
            return list(self._reviews.values())

    async def _invoke_analysis_model(self, pr_id: str, payload: WebhookPayload) -> Dict[str, Any]:
        messages = self._build_analysis_messages(pr_id, payload)
        try:
            response = await asyncio.to_thread(
                call_chat_completion,
                self._analysis_model,
                messages,
                max_tokens=2048,
                stream=False,
                temperature=0.1,
            )
            return self._parse_analysis_response(pr_id, response, payload)
        except Exception as exc:  # pragma: no cover - LLM failures handled gracefully
            logger.error("DeepSeek analysis failed: %s", exc, exc_info=True)
            return self._fallback_review(pr_id, payload)

    def _build_analysis_messages(self, pr_id: str, payload: WebhookPayload) -> List[Dict[str, str]]:
        file_snippets: List[str] = []
        for file in payload.files[:10]:
            snippet = file.content[:1_500]
            file_snippets.append(
                f"File: {file.path}\nLanguage: {file.language}\nSnippet:\n{snippet}"
            )
        files_section = "\n\n".join(file_snippets) if file_snippets else "No file diffs provided."
        instructions = (
            "Analyse the pull request diff and report code review findings. "
            "Respond strictly in JSON with keys 'summary' and 'findings'. "
            "Each finding must include 'file_path', 'line_number', 'severity' "
            "('critical', 'major', 'minor'), 'category' "
            "('security','performance','bug','style','test_gap'), 'description', "
            "'suggested_fix', and 'confidence_score' between 0 and 1."
        )
        return [
            {
                "role": "system",
                "content": (
                    "You are TraceFox DeepSeek, a senior staff engineer performing precise code reviews."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{instructions}\n\n"
                    f"PR ID: {pr_id}\n"
                    f"Repository: {payload.repository.name}\n"
                    f"Title: {payload.pull_request.title}\n"
                    f"Author: {payload.pull_request.author}\n"
                    f"Files:\n{files_section}"
                ),
            },
        ]

    def _parse_analysis_response(
        self,
        pr_id: str,
        response: Dict[str, Any],
        payload: WebhookPayload,
    ) -> Dict[str, Any]:
        choices = response.get("choices") or []
        if not choices:
            raise ValueError("Missing choices in DeepSeek response")
        content = choices[0].get("message", {}).get("content", "")
        structured = self._safe_load_json(content)
        summary_text = structured.get("summary") or f"No actionable issues found for PR {pr_id}."
        findings_payload = structured.get("findings") or []
        findings = self._build_findings(findings_payload)
        if not findings:
            findings = self._fallback_review(pr_id, payload)["findings"]
        return {"summary": summary_text, "findings": findings}

    def _build_findings(self, findings_payload: List[Dict[str, Any]]) -> List[ReviewFinding]:
        results: List[ReviewFinding] = []
        for item in findings_payload:
            try:
                severity = Severity(item.get("severity", "minor"))
            except ValueError:
                severity = Severity.minor
            try:
                category = FindingCategory(item.get("category", "bug"))
            except ValueError:
                category = FindingCategory.bug
            try:
                finding = ReviewFinding(
                    id=str(uuid4()),
                    file_path=str(item.get("file_path") or "unknown.py"),
                    line_number=int(item.get("line_number") or 1),
                    severity=severity,
                    category=category,
                    description=str(item.get("description") or "Unspecified issue."),
                    suggested_fix=item.get("suggested_fix"),
                    confidence_score=float(item.get("confidence_score") or 0.5),
                    code_diff=item.get("code_diff"),
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Skipping invalid finding payload %s: %s", item, exc)
                continue
            results.append(finding)
        return results

    def _safe_load_json(self, content: str) -> Dict[str, Any]:
        content = content.strip()
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Attempt to recover by extracting JSON between code fences.
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    logger.debug("Unable to parse JSON from DeepSeek content: %s", content)
        return {}

    def _fallback_review(self, pr_id: str, payload: WebhookPayload) -> Dict[str, Any]:
        finding = ReviewFinding(
            id=str(uuid4()),
            file_path=payload.files[0].path if payload.files else "unknown.py",
            line_number=1,
            severity=Severity.minor,
            category=FindingCategory.style,
            description="Automated analysis unavailable. Manual review suggested.",
            suggested_fix="Re-run TraceFox review once LLM connectivity is restored.",
            confidence_score=0.3,
        )
        return {
            "summary": f"TraceFox fallback: unable to analyse PR {pr_id} using DeepSeek-R1.",
            "findings": [finding],
        }
