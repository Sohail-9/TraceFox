from __future__ import annotations

from typing import Dict, List

from services.common.models import AnomalyAlert


class ProductionMonitorService:
    """Performs lightweight anomaly detection on deployment metrics."""

    def analyse_metrics(self, metrics: List[Dict[str, float]]) -> List[AnomalyAlert]:
        alerts: List[AnomalyAlert] = []
        for metric in metrics:
            name = metric["name"]
            value = float(metric["value"])
            unit = metric.get("unit", "")
            baseline = self._baseline(name)
            severity, flagged = self._is_anomalous(name, value, baseline)
            if not flagged:
                continue
            alerts.append(
                AnomalyAlert(
                    metric=f"{name} ({unit})".strip(),
                    observed=value,
                    baseline=baseline,
                    severity=severity,
                    methodology="IsolationForest (simulated)",
                )
            )
        return alerts

    def _baseline(self, name: str) -> float:
        defaults = {
            "latency_ms_p95": 320.0,
            "error_rate": 0.02,
            "cpu_usage": 55.0,
        }
        return defaults.get(name, 1.0)

    def _is_anomalous(self, name: str, value: float, baseline: float) -> tuple[str, bool]:
        threshold_multiplier = 1.5 if name == "latency_ms_p95" else 2.0
        if value > baseline * threshold_multiplier:
            return ("critical" if value > baseline * (threshold_multiplier + 0.5) else "warning", True)
        return ("info", False)
