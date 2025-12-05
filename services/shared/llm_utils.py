"""Utility helpers for interacting with TraceFox LLM providers.

This module centralises provider metadata, pricing and calling conventions for
our two supported models:

* DeepSeek-AI ``DeepSeek-R1`` (primary reasoning model)
* Ola Krutrim ``Gemma-3-27B-IT`` (grounded code assistant)

It removes legacy GPT references and adapts to provider credentials supplied
via the TraceFox configuration system / environment variables.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import httpx

try:  # Optional dependency used for accurate token accounting.
    import tiktoken  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - tiktoken is optional
    tiktoken = None  # type: ignore

from services.shared.config import ConfigurationError, get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pricing expressed as USD per token (per 1 token, not per 1K/M).
# ---------------------------------------------------------------------------
PRICING: Dict[str, Dict[str, float]] = {
    "DeepSeek-R1": {
        "input": 0.00000084942,  # $0.084942 per 100k input tokens
        "cached_input": 0.00000042471,
        "output": 0.00000347490,  # $0.34749 per 100k output tokens
    },
    "Gemma-3-27B-IT": {
        "input": 0.00000061776,  # $0.061776 per 100k input tokens
        "cached_input": 0.00000030888,
        "output": 0.00000193050,  # $0.19305 per 100k output tokens
    },
}


# ---------------------------------------------------------------------------
# Provider + model metadata
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProviderMetadata:
    provider_key: str
    model_name: str
    default_endpoint: str
    completion_path: str
    max_context_tokens: int = 128_000
    max_completion_tokens: int = 4_096
    supports_stream: bool = True
    supports_structured_content: bool = True
    supports_functions: bool = False


MODEL_REGISTRY: Dict[str, ProviderMetadata] = {
    "deepseek-r1": ProviderMetadata(
        provider_key="ola_krutrim",
        model_name="DeepSeek-R1",
        default_endpoint="https://cloud.olakrutrim.com/v1",
        completion_path="/chat/completions",
        supports_structured_content=True,
        supports_stream=True,
    ),
    "gemma-3-27b-it": ProviderMetadata(
        provider_key="ola_krutrim",
        model_name="Gemma-3-27B-IT",
        default_endpoint="https://cloud.olakrutrim.com/v1",
        completion_path="/chat/completions",
        supports_structured_content=False,
        supports_stream=False,
    ),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _normalise_model_name(model: str) -> str:
    return model.strip().lower()


def _resolve_metadata(model: str) -> ProviderMetadata:
    key = _normalise_model_name(model)
    metadata = MODEL_REGISTRY.get(key)
    if metadata is None:
        raise ConfigurationError(f"Unsupported model '{model}'. Available: {sorted(MODEL_REGISTRY)}")
    return metadata


def _resolve_provider_config(provider_key: str) -> Mapping[str, Any]:
    settings = get_settings()
    provider_config = settings.ai_models.providers.get(provider_key)
    if not provider_config:
        raise ConfigurationError(f"LLM provider '{provider_key}' is not configured")
    if not isinstance(provider_config, Mapping):
        raise ConfigurationError(f"LLM provider '{provider_key}' configuration must be a mapping")
    return provider_config


def _resolve_api_key(provider_key: str, provider_config: Mapping[str, Any]) -> str:
    # Prefer explicit api_key, then api_key_env, then TRACEFOX_{PROVIDER_KEY}_API_KEY.
    api_key = provider_config.get("api_key")
    if api_key:
        return str(api_key)

    env_name = provider_config.get("api_key_env")
    if env_name:
        api_key_env = os.getenv(str(env_name))
        if api_key_env:
            return api_key_env

    fallback_env = f"TRACEFOX_{provider_key.upper()}_API_KEY"
    api_key_env = os.getenv(fallback_env)
    if api_key_env:
        return api_key_env

    raise ConfigurationError(
        f"API key for provider '{provider_key}' not configured. "
        f"Set 'api_key', specify 'api_key_env', or export {fallback_env}."
    )


def _build_headers(api_key: str, provider_config: Mapping[str, Any]) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    extra_headers = provider_config.get("headers")
    if isinstance(extra_headers, Mapping):
        headers.update({str(k): str(v) for k, v in extra_headers.items()})
    return headers


@dataclass(frozen=True)
class LLMContext:
    model: str
    provider: str
    base_url: str
    completion_path: str
    headers: Mapping[str, str]
    timeout: float
    supports_stream: bool
    supports_structured_content: bool
    supports_functions: bool
    max_context_tokens: int
    max_completion_tokens: int


def get_llm_context(model: str) -> LLMContext:
    metadata = _resolve_metadata(model)
    provider_config = _resolve_provider_config(metadata.provider_key)

    endpoint = provider_config.get("endpoint") or provider_config.get("base_url") or metadata.default_endpoint
    timeout = float(provider_config.get("timeout", 60.0))

    api_key = _resolve_api_key(metadata.provider_key, provider_config)
    headers = _build_headers(api_key, provider_config)

    return LLMContext(
        model=metadata.model_name,
        provider=metadata.provider_key,
        base_url=str(endpoint).rstrip("/"),
        completion_path=metadata.completion_path,
        headers=headers,
        timeout=timeout,
        supports_stream=metadata.supports_stream,
        supports_structured_content=metadata.supports_structured_content,
        supports_functions=metadata.supports_functions,
        max_context_tokens=metadata.max_context_tokens,
        max_completion_tokens=metadata.max_completion_tokens,
    )


# ---------------------------------------------------------------------------
# Cost + usage helpers
# ---------------------------------------------------------------------------
def extract_token_usage(response_json: Mapping[str, Any]) -> Tuple[int, int]:
    usage = response_json.get("usage")
    if isinstance(usage, Mapping):
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        if prompt_tokens == 0 and completion_tokens == 0:
            logger.debug("Usage payload present but zero tokens: %s", json.dumps(response_json, default=str)[:400])
        return prompt_tokens, completion_tokens
    return 0, 0


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = PRICING.get(model)
    if not pricing:
        logger.warning("No pricing data available for model '%s'", model)
        return 0.0
    input_cost = pricing["input"] * (prompt_tokens or 0)
    output_cost = pricing["output"] * (completion_tokens or 0)
    return input_cost + output_cost


def get_max_token_limit(model: str) -> int:
    return _resolve_metadata(model).max_context_tokens


def get_max_completion_token_limit(model: str) -> int:
    return _resolve_metadata(model).max_completion_tokens


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------
def _get_encoding(model: str):
    if tiktoken is None:
        raise RuntimeError(
            "tiktoken is required for token counting but is not installed. "
            "Install tiktoken or guard calls to num_tokens_from_string."
        )
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.encoding_for_model("gpt-3.5-turbo")


def num_tokens_from_string(text: Any, model: str) -> int:
    if isinstance(text, Mapping):
        text = text.get("content", "")
    if not isinstance(text, str):
        text = str(text)
    if tiktoken is None:
        return len(text.split())
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


def count_tokens_in_messages(messages: Iterable[Mapping[str, Any]], model: str) -> int:
    if tiktoken is None:
        return sum(len(str(message.get("content", "")).split()) for message in messages)
    encoding = _get_encoding(model)
    total = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts: List[str] = []
            for part in content:
                if isinstance(part, Mapping) and part.get("type") == "text":
                    text_parts.append(str(part.get("text", "")))
            content = " ".join(text_parts)
        if not isinstance(content, str):
            content = str(content)
        total += len(encoding.encode(content))
    return total


# ---------------------------------------------------------------------------
# Capability surface
# ---------------------------------------------------------------------------
def get_model_capabilities(model: str) -> Dict[str, Any]:
    metadata = _resolve_metadata(model)
    return {
        "supports_functions": metadata.supports_functions,
        "supports_stream_options": metadata.supports_stream,
        "supports_structured_content": metadata.supports_structured_content,
        "provider": metadata.provider_key,
    }


def supports_function_calling(model: str) -> bool:
    return get_model_capabilities(model)["supports_functions"]


def supports_stream_options(model: str) -> bool:
    return get_model_capabilities(model)["supports_stream_options"]


# ---------------------------------------------------------------------------
# Payload preparation + call execution
# ---------------------------------------------------------------------------
def _flatten_structured_content(message: MutableMapping[str, Any]) -> None:
    content = message.get("content")
    if isinstance(content, list):
        text_parts: List[str] = []
        for part in content:
            if isinstance(part, Mapping) and part.get("type") == "text":
                text_parts.append(str(part.get("text", "")))
        message["content"] = " ".join(text_parts)


def prepare_llm_payload(model: str, messages: List[MutableMapping[str, Any]], *, functions: Optional[List[Mapping[str, Any]]] = None, stream: Optional[bool] = None, **extra: Any) -> Dict[str, Any]:
    context = get_llm_context(model)

    prepared_messages: List[MutableMapping[str, Any]] = []
    for original in messages:
        message = dict(original)
        if not context.supports_structured_content:
            _flatten_structured_content(message)
        prepared_messages.append(message)

    payload: Dict[str, Any] = {
        "model": context.model,
        "messages": prepared_messages,
    }

    if stream is None:
        stream = context.supports_stream
    payload["stream"] = bool(stream)

    if functions and context.supports_functions:
        payload["functions"] = functions

    payload.update(extra)
    return payload


def call_chat_completion(
    model: str,
    messages: List[MutableMapping[str, Any]],
    *,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    stream: Optional[bool] = None,
    **extra: Any,
) -> Dict[str, Any]:
    context = get_llm_context(model)
    payload = prepare_llm_payload(
        model,
        messages,
        stream=stream,
        max_tokens=max_tokens or context.max_completion_tokens,
        temperature=temperature if temperature is not None else get_settings().ai_models.default_temperature,
        top_p=top_p,
        **extra,
    )

    url = f"{context.base_url}{context.completion_path}"
    logger.debug("Calling LLM provider '%s' model '%s' at %s", context.provider, context.model, url)

    try:
        with httpx.Client(timeout=context.timeout) as client:
            response = client.post(url, json=payload, headers=context.headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - network layer
        logger.error(
            "LLM provider '%s' returned HTTP %s: %s",
            context.provider,
            exc.response.status_code,
            exc.response.text[:400],
        )
        raise
    except httpx.HTTPError as exc:  # pragma: no cover - network layer
        logger.error("LLM provider '%s' request failed: %s", context.provider, exc)
        raise


__all__ = [
    "PRICING",
    "LLMContext",
    "calculate_cost",
    "call_chat_completion",
    "count_tokens_in_messages",
    "extract_token_usage",
    "get_llm_context",
    "get_max_completion_token_limit",
    "get_max_token_limit",
    "get_model_capabilities",
    "num_tokens_from_string",
    "prepare_llm_payload",
    "supports_function_calling",
    "supports_stream_options",
]
