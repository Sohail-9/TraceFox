"""LLM client abstractions for Loa Krutrim (DeepSeek) and local Llama models."""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

import httpx

from services.shared.config import ConfigurationError, get_settings

logger = logging.getLogger(__name__)


class LoaKrutrimClient:
    """HTTP client wrapper for DeepSeek models served through the Loa Krutrim API."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        provider_cfg = settings.ai_models.providers.get("ola_krutrim", {}) if settings.ai_models else {}
        resolved_api_key = api_key or provider_cfg.get("api_key")
        if not resolved_api_key:
            env_hint = provider_cfg.get("api_key_env")
            if env_hint:
                resolved_api_key = os.getenv(str(env_hint))
        if not resolved_api_key:
            env_candidates = [
                "TRACEFOX_OLA_KRUTRIM_API_KEY",
                "TRACEFOX_OLA_KRUTRIM__API_KEY",
                "KRUTRIM_API_KEY",
            ]
            for candidate in env_candidates:
                resolved_api_key = os.getenv(candidate)
                if resolved_api_key:
                    break
        if not resolved_api_key:
            env_hint = provider_cfg.get("api_key_env") or "TRACEFOX_OLA_KRUTRIM__API_KEY"
            raise ConfigurationError(
                "Loa Krutrim API key not configured. "
                f"Set ai_models.providers.ola_krutrim.api_key or export {env_hint}."
            )
        resolved_base = base_url or provider_cfg.get("endpoint") or "https://api.loa-krutrim.com/v1"
        self.api_key = resolved_api_key
        self.base_url = resolved_base.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    def analyze_code(self, code: str, analysis_type: str, *, max_tokens: int = 2048) -> Dict:
        prompt = self._format_analysis_prompt(code, analysis_type)
        payload = {
            "model": "deepseek-coder-67b",
            "messages": [
                {"role": "system", "content": self._get_system_prompt(analysis_type)},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": max_tokens,
        }
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if response.status_code == httpx.codes.OK:
                data = response.json()
                return {
                    "status": "success",
                    "response": data["choices"][0]["message"]["content"],
                    "model": "deepseek-coder-67b",
                    "usage": data.get("usage", {}),
                }
            logger.error("Loa Krutrim API error %s: %s", response.status_code, response.text[:400])
            return {"status": "error", "error": response.text, "model": "deepseek-coder-67b"}
        except httpx.HTTPError as exc:
            logger.error("Loa Krutrim request failed: %s", exc)
            return {"status": "error", "error": str(exc), "model": "deepseek-coder-67b"}

    def _get_system_prompt(self, analysis_type: str) -> str:
        prompts = {
            "breaking_changes": (
                "You are an expert code reviewer analyzing for breaking changes. "
                "Identify changes that can break dependent functionality and propose mitigations."
            ),
            "security": (
                "You are a security expert reviewing code for vulnerabilities. "
                "Identify exploitable issues, compliance risks, and suggest fixes."
            ),
            "performance": (
                "You are a performance optimization expert. "
                "Locate bottlenecks and recommend precise improvements."
            ),
            "cross_layer": (
                "You are analyzing code for cross-layer consistency issues across frontend/backend/data layers."
            ),
        }
        return prompts.get(analysis_type, prompts["breaking_changes"])

    def _format_analysis_prompt(self, code: str, analysis_type: str) -> str:
        return (
            f"Analyze the following code change for {analysis_type}:\n"
            f"{code}\n"
            "Provide detailed analysis in JSON with keys: findings, severity, impact, recommendations, confidence."
        )


class LlamaClient:
    """Client for local Llama inference served by Ollama/vLLM compatible endpoints."""

    def __init__(
        self,
        model_name: str = "llama3",
        *,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        settings = get_settings()
        provider_cfg = settings.ai_models.providers.get("llama_local", {}) if settings.ai_models else {}
        self.model_name = model_name or provider_cfg.get("model", "llama3")
        resolved_base = base_url or provider_cfg.get("endpoint") or "http://localhost:11434"
        self.base_url = resolved_base.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    def generate(self, prompt: str, *, max_tokens: int = 512, temperature: float = 0.1) -> Dict:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        try:
            response = self._client.post(f"{self.base_url}/api/generate", json=payload)
            if response.status_code == httpx.codes.OK:
                data = response.json()
                return {"status": "success", "response": data.get("response", ""), "model": self.model_name}
            logger.error("Llama inference error %s: %s", response.status_code, response.text[:400])
            return {"status": "error", "error": response.text, "model": self.model_name}
        except httpx.HTTPError as exc:
            logger.error("Llama inference failed: %s", exc)
            return {"status": "error", "error": str(exc), "model": self.model_name}

    def batch_generate(self, prompts: List[str], *, max_tokens: int = 512) -> List[Dict]:
        results: List[Dict] = []
        for prompt in prompts:
            results.append(self.generate(prompt, max_tokens=max_tokens))
        return results
