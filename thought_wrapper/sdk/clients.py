"""Provider clients for OpenAI, Anthropic, xAI, Ollama, and llama.cpp."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    provider_name: str

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:  # pragma: no cover - protocol
        ...


def _http_json(
    url: str,
    payload: dict,
    *,
    headers: dict[str, str],
    timeout_s: float = 60.0,
) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        msg = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {msg}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network dependent
        raise RuntimeError(f"Network error calling {url}: {exc}") from exc


@dataclass
class OpenAIClient:
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    provider_name: str = "openai"

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Missing OpenAI API key")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = _http_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {key}"},
        )
        return str(data["choices"][0]["message"]["content"])


@dataclass
class AnthropicClient:
    api_key: str | None = None
    base_url: str = "https://api.anthropic.com/v1"
    anthropic_version: str = "2023-06-01"
    provider_name: str = "anthropic"

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("Missing Anthropic API key")
        payload = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = _http_json(
            f"{self.base_url.rstrip('/')}/messages",
            payload,
            headers={"x-api-key": key, "anthropic-version": self.anthropic_version},
        )
        content = data.get("content", [])
        if isinstance(content, list) and content:
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return str(block.get("text", ""))
        raise RuntimeError(f"Unexpected Anthropic response format: {data}")


@dataclass
class XAIClient:
    api_key: str | None = None
    base_url: str = "https://api.x.ai/v1"
    provider_name: str = "xai"

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        key = self.api_key or os.getenv("XAI_API_KEY")
        if not key:
            raise RuntimeError("Missing xAI API key")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = _http_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {key}"},
        )
        return str(data["choices"][0]["message"]["content"])


@dataclass
class OllamaClient:
    base_url: str = "http://localhost:11434"
    provider_name: str = "ollama"

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        data = _http_json(f"{self.base_url.rstrip('/')}/api/chat", payload, headers={})
        if "message" in data and isinstance(data["message"], dict):
            return str(data["message"].get("content", ""))
        raise RuntimeError(f"Unexpected Ollama response format: {data}")


@dataclass
class LlamaCppClient:
    """llama.cpp OpenAI-compatible HTTP server client."""

    base_url: str = "http://localhost:8080/v1"
    api_key: str | None = None
    provider_name: str = "llama.cpp"

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers: dict[str, str] = {}
        key = self.api_key or os.getenv("LLAMACPP_API_KEY")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        data = _http_json(f"{self.base_url.rstrip('/')}/chat/completions", payload, headers=headers)
        return str(data["choices"][0]["message"]["content"])

