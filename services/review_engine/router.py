from __future__ import annotations

from typing import Dict


class ModelRouter:
    """Routes analysis stages to the optimal model/provider as defined in the LLD."""

    def __init__(self) -> None:
        self._routing_rules: Dict[str, Dict[str, str]] = {
            "quick_filter": {
                "model": "llama",
                "version": "3-8b",
                "reason": "Fast filtering and syntax checks",
            },
            "security": {
                "model": "llama",
                "version": "2-70b",
                "reason": "Security heuristics and style validation",
            },
            "breaking_changes": {
                "model": "deepseek",
                "version": "coder-67b",
                "reason": "Complex reasoning for cross-file impacts",
            },
            "performance": {
                "model": "deepseek",
                "version": "coder-67b",
                "reason": "Handles optimisation and regression detection",
            },
            "cross_layer": {
                "model": "deepseek",
                "version": "coder-67b",
                "reason": "Multi-system reasoning across layers",
            },
        }

    def route_analysis(self, analysis_type: str) -> Dict[str, str]:
        rule = self._routing_rules.get(analysis_type)
        if rule is None:
            return self._routing_rules["security"]
        return rule
