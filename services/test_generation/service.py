from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from services.code_analysis.service import FileAnalysis


@dataclass
class GeneratedTestCase:
    name: str
    description: str
    priority: str
    suggested_assertions: List[str]


class TestGenerationService:
    """Lightweight heuristic-based test generator for the MVP."""

    def generate(
        self, analyses: List[FileAnalysis], commit_id: str
    ) -> Dict[str, List[GeneratedTestCase]]:
        generated: List[GeneratedTestCase] = []

        for analysis in analyses:
            priority = self._map_priority(analysis.risk_level)
            generated.append(
                GeneratedTestCase(
                    name=self._build_test_name(commit_id, analysis),
                    description=self._build_description(analysis),
                    priority=priority,
                    suggested_assertions=self._suggest_assertions(analysis),
                )
            )

        return {"tests": generated}

    def _map_priority(self, risk_level: str) -> str:
        mapping = {"high": "P0", "medium": "P1", "low": "P2"}
        return mapping.get(risk_level, "P2")

    def _build_test_name(self, commit_id: str, analysis: FileAnalysis) -> str:
        short_commit = commit_id[:7] if commit_id else "unknown"
        suffix = analysis.path.replace("/", "_").replace(".", "_")
        return f"test_{short_commit}_{suffix}"

    def _build_description(self, analysis: FileAnalysis) -> str:
        return (
            f"Validate the behaviour of {analysis.path} after structural changes. "
            f"Detected {analysis.ast_summary.get('functions', 0)} functions, "
            f"{analysis.ast_summary.get('classes', 0)} classes. "
            f"Risk level: {analysis.risk_level}."
        )

    def _suggest_assertions(self, analysis: FileAnalysis) -> List[str]:
        suggestions: List[str] = []
        if analysis.ast_summary.get("try_blocks", 0):
            suggestions.append("Ensure error handling paths raise expected exceptions.")
        if analysis.ast_summary.get("conditionals", 0) >= 3:
            suggestions.append("Cover both success and failure branches in conditional logic.")
        if analysis.ast_summary.get("functions", 0) >= 2:
            suggestions.append("Add regression assertions for new public functions.")
        if not suggestions:
            suggestions.append("Add smoke test to confirm key outputs remain stable.")
        return suggestions
