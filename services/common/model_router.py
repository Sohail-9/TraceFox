from __future__ import annotations

BASE_MODEL = "Krutrim-DeepSeek-R1"


class ModelRouter:
    """Routes workload to the appropriate model name based on heuristics."""

    def select_for_code_analysis(self, language: str, file_size: int) -> str:
        if language.lower() != "python" or file_size > 5_000:
            return "CodeLlama-34B"
        return BASE_MODEL

    def select_for_tests(self, risk_level: str, locale: str) -> str:
        if locale in {"hi", "ta", "te", "bn", "mr"}:
            return "Krutrim-V2"
        if risk_level == "high":
            return "GPT-4 Turbo"
        if risk_level == "medium":
            return "Claude-3.5-Sonnet"
        return BASE_MODEL

    def select_for_rca(self, severity: str, locale: str) -> str:
        if locale in {"hi", "ta", "te", "bn", "mr"}:
            return "Krutrim-V2"
        if severity == "high":
            return "GPT-4 Turbo"
        return BASE_MODEL
