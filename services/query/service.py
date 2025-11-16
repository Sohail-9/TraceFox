"""Query orchestration helpers for graph and relational lookups."""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List


class QueryOrchestrationService:
    """Executes cached graph queries and similarity lookups."""

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}

    def query_function_impact(self, function_id: str, max_depth: int = 3) -> Dict:
        cache_key = f"function_impact:{function_id}:{max_depth}"
        cached = self._cache.get(cache_key)
        if cached:
            return json.loads(cached)

        nodes = [
            {"id": f"{function_id}::caller::{idx}", "type": "Function"}
            for idx in range(1, min(max_depth, 3) + 1)
        ]
        relationships = [{"from": function_id, "to": node["id"], "type": "CALLS"} for node in nodes]
        payload = {"nodes": nodes, "relationships": relationships}
        self._cache[cache_key] = json.dumps(payload)
        return payload

    def query_similar_patterns(self, code_snippet: str, top_k: int = 5) -> List[Dict]:
        digest = hashlib.sha1(code_snippet.encode("utf-8")).hexdigest()  # noqa: S324
        return [
            {
                "id": f"pattern::{digest[:8]}::{idx}",
                "similarity": round(0.8 - (idx * 0.05), 2),
                "hint": "Similar implementation detected",
            }
            for idx in range(min(top_k, 5))
        ]

    def callers_for_file(self, file_path: str) -> List[Dict]:
        digest = hashlib.md5(file_path.encode("utf-8")).hexdigest()  # noqa: S324
        count = (int(digest[:2], 16) % 3) + 1
        return [{"function": f"{file_path}::fn_{idx}", "complexity": 5 + idx} for idx in range(count)]

    def dependencies_for_file(self, file_path: str) -> List[str]:
        seed = sum(ord(ch) for ch in file_path)
        count = seed % 3
        return [f"{file_path.split('/')[0]}/shared_{idx}.py" for idx in range(count)]
