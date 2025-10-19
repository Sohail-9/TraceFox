from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import ast


@dataclass
class FileChange:
    path: str
    content: str
    language: str = "python"


@dataclass
class FileAnalysis:
    path: str
    ast_summary: Dict[str, int]
    complexity_score: float
    risk_level: str
    warnings: List[str]


class CodeAnalysisService:
    """Very small code analysis stub to power the TraceFox MVP pipeline."""

    def analyze(self, files: List[FileChange]) -> Dict[str, List[FileAnalysis]]:
        analyses: List[FileAnalysis] = []
        for file in files:
            if file.language.lower() != "python":
                analyses.append(
                    FileAnalysis(
                        path=file.path,
                        ast_summary={},
                        complexity_score=5.0,
                        risk_level="medium",
                        warnings=[f"Unsupported language: {file.language}"],
                    )
                )
                continue

            ast_summary, warnings = self._build_ast_summary(file)
            complexity_score = self._estimate_complexity(ast_summary)
            risk_level = self._determine_risk(complexity_score, warnings)

            analyses.append(
                FileAnalysis(
                    path=file.path,
                    ast_summary=ast_summary,
                    complexity_score=complexity_score,
                    risk_level=risk_level,
                    warnings=warnings,
                )
            )

        overall_risk = self._summarise_platform_risk(analyses)
        return {
            "files": analyses,
            "summary": {
                "overall_risk": overall_risk,
                "average_complexity": round(
                    sum(a.complexity_score for a in analyses) / len(analyses), 2
                )
                if analyses
                else 0.0,
            },
        }

    def _build_ast_summary(self, file: FileChange) -> tuple[Dict[str, int], List[str]]:
        warnings: List[str] = []
        try:
            tree = ast.parse(file.content)
        except SyntaxError as exc:
            warnings.append(f"Syntax error: {exc.msg} (line {exc.lineno})")
            return {"syntax_errors": 1}, warnings

        functions = sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
        async_functions = sum(
            isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(tree)
        )
        classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
        conditionals = sum(isinstance(node, ast.If) for node in ast.walk(tree))
        loops = sum(
            isinstance(node, (ast.For, ast.AsyncFor, ast.While))
            for node in ast.walk(tree)
        )
        try_blocks = sum(isinstance(node, ast.Try) for node in ast.walk(tree))

        return (
            {
                "functions": functions,
                "async_functions": async_functions,
                "classes": classes,
                "conditionals": conditionals,
                "loops": loops,
                "try_blocks": try_blocks,
            },
            warnings,
        )

    def _estimate_complexity(self, ast_summary: Dict[str, int]) -> float:
        if "syntax_errors" in ast_summary:
            return 10.0

        weightings = {
            "functions": 1.0,
            "async_functions": 1.5,
            "classes": 1.2,
            "conditionals": 0.8,
            "loops": 1.3,
            "try_blocks": 1.8,
        }

        score = sum(
            ast_summary.get(key, 0) * weight for key, weight in weightings.items()
        )
        return round(min(score / 2.0, 10.0), 2)

    def _determine_risk(self, complexity_score: float, warnings: List[str]) -> str:
        if warnings or complexity_score >= 7.5:
            return "high"
        if complexity_score >= 4.5:
            return "medium"
        return "low"

    def _summarise_platform_risk(self, analyses: List[FileAnalysis]) -> str:
        risk_order = {"low": 0, "medium": 1, "high": 2}
        highest = max((risk_order[a.risk_level] for a in analyses), default=0)
        reverse = {v: k for k, v in risk_order.items()}
        return reverse[highest]


def build_file_changes(payload: List[Dict[str, str]]) -> List[FileChange]:
    return [
        FileChange(
            path=item["path"],
            content=item["content"],
            language=item.get("language", "python"),
        )
        for item in payload
    ]

