from __future__ import annotations

from typing import List, Optional


class KnowledgeBaseService:
    """Static in-memory incident knowledge base for the POC."""

    _INCIDENTS: List[str] = [
        "Issue #234: Route change from /users/:id to /api/v2/users/:id broke the mobile client.",
        "Incident #412: Missing null guard introduced flakiness in account_summary tests.",
        "Outage #88: Long-running async task starved event loop causing latency spikes.",
    ]

    def lookup_by_keywords(self, text: str) -> Optional[str]:
        lowered = text.lower()
        for incident in self._INCIDENTS:
            if any(keyword in lowered for keyword in self._keyword_map(incident)):
                return incident
        return None

    def _keyword_map(self, incident: str) -> List[str]:
        if "route change" in incident.lower():
            return ["route", "404", "api"]
        if "null guard" in incident.lower():
            return ["null", "none", "flaky"]
        if "async task" in incident.lower():
            return ["async", "latency", "event loop"]
        return ["regression"]

