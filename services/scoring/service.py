"""Confidence scoring heuristics for TraceFox findings."""

from __future__ import annotations

from typing import Dict

from services.shared.models import Finding, FindingCategory, FindingPriority, FindingSeverity


class ConfidenceScoringService:
    """Implements ensemble-style confidence calculation and severity classification."""

    def __init__(self) -> None:
        self.model_accuracy: Dict[str, Dict[str, float]] = {
            "llama": {"true_positive_rate": 0.85, "false_positive_rate": 0.15},
            "deepseek": {"true_positive_rate": 0.91, "false_positive_rate": 0.09},
            "graph": {"true_positive_rate": 0.78, "false_positive_rate": 0.18},
        }
        self._historical_accuracy: Dict[FindingCategory, float] = {
            FindingCategory.security: 0.88,
            FindingCategory.performance: 0.82,
            FindingCategory.style: 0.75,
            FindingCategory.logic: 0.86,
            FindingCategory.breaking_change: 0.9,
            FindingCategory.cross_layer: 0.83,
        }

    def calculate_confidence(self, finding: Finding) -> float:
        deviation_score = self._calculate_pattern_deviation(finding) * 0.4
        context_score = self._calculate_context_relevance(finding) * 0.3
        historical_score = self._calculate_historical_accuracy(finding.type) * 0.2
        validation_score = self._calculate_cross_validation(finding) * 0.1

        base_confidence = deviation_score + context_score + historical_score + validation_score
        source_key = str(finding.source_model)
        model_multiplier = self.model_accuracy.get(source_key, {}).get("true_positive_rate", 0.8)
        final_confidence = base_confidence * model_multiplier
        return max(0.0, min(1.0, final_confidence))

    def classify_severity(self, confidence: float) -> FindingPriority:
        if confidence >= 0.90:
            return FindingPriority.must_fix
        if confidence >= 0.70:
            return FindingPriority.should_fix
        if confidence >= 0.50:
            return FindingPriority.nice_to_fix
        return FindingPriority.suppressed

    def _calculate_pattern_deviation(self, finding: Finding) -> float:
        weights = {
            FindingSeverity.high: 0.95,
            FindingSeverity.medium: 0.8,
            FindingSeverity.low: 0.65,
        }
        base = weights.get(finding.severity, 0.6)
        coverage_hint = finding.metadata.get("affected_components", 1)
        modifier = min(coverage_hint / 3.0, 0.2)
        return min(1.0, base + modifier)

    def _calculate_context_relevance(self, finding: Finding) -> float:
        overlap = finding.metadata.get("context_overlap", 0.5)
        dependency_weight = finding.metadata.get("dependency_depth", 1)
        return min(1.0, 0.4 + overlap * 0.4 + min(dependency_weight, 3) * 0.05)

    def _calculate_historical_accuracy(self, category: FindingCategory) -> float:
        return self._historical_accuracy.get(category, 0.7)

    def _calculate_cross_validation(self, finding: Finding) -> float:
        corroborating = finding.metadata.get("corroborating_signals", 0)
        if corroborating <= 0:
            return 0.4
        if corroborating >= 3:
            return 0.95
        return 0.6 + (corroborating * 0.1)
