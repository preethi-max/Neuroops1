"""NeuroOps Model Provider Layer.

Abstracts AI model calls so agents never hardcode a single provider.
Supports OpenAI, Google Gemini, and Anthropic Claude through a common
interface. Falls back to a deterministic stub when no API keys are set.
"""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from utils import logger


class ModelResponse:
    """Normalized response from any provider."""

    def __init__(self, content: str, confidence: float, provider: str, model: str, raw: Optional[dict] = None):
        self.content = content
        self.confidence = confidence
        self.provider = provider
        self.model = model
        self.raw = raw or {}

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "confidence": self.confidence,
            "provider": self.provider,
            "model": self.model,
        }


class BaseModelProvider(ABC):
    """Common interface every provider implements."""

    name: str = "base"

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> ModelResponse:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Stub provider (no API key needed — deterministic heuristic output)
# ---------------------------------------------------------------------------

class StubProvider(BaseModelProvider):
    name = "stub"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> ModelResponse:
        text = user_prompt.strip()
        words = len(text.split())
        # Produce a structured heuristic response based on keywords.
        output_lines = [f"[Stub Model] Processed request ({words} words):"]
        if re.search(r"\b(code|function|api|endpoint|class)\b", text, re.I):
            output_lines.append("- Detected: code generation task")
            output_lines.append("- Suggested approach: modular functions with error handling")
        if re.search(r"\b(debug|fix|bug|error|crash)\b", text, re.I):
            output_lines.append("- Detected: debugging task")
            output_lines.append("- Suggested approach: isolate failing path, add logging, narrow exception scope")
        if re.search(r"\b(design|ui|ux|layout|wireframe)\b", text, re.I):
            output_lines.append("- Detected: design task")
            output_lines.append("- Suggested approach: 8px grid, WCAG AA contrast, progressive disclosure")
        if re.search(r"\b(test|qa|security|vulnerab)\b", text, re.I):
            output_lines.append("- Detected: testing task")
            output_lines.append("- Suggested approach: unit + integration tests, boundary cases")
        if re.search(r"\b(document|readme|guide|manual)\b", text, re.I):
            output_lines.append("- Detected: documentation task")
            output_lines.append("- Suggested approach: overview, usage, parameters, examples")
        if not any("- Detected" in line for line in output_lines[1:]):
            output_lines.append("- Detected: general task")
            output_lines.append("- Suggested approach: decompose into subtasks, research, implement, review")
        confidence = min(0.95, 0.6 + words / 200.0)
        return ModelResponse(
            content="\n".join(output_lines),
            confidence=confidence,
            provider=self.name,
            model="stub-v1",
        )


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(BaseModelProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> ModelResponse:
        import httpx

        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": kwargs.get("temperature", 0.3),
            },
            timeout=kwargs.get("timeout", 30),
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ModelResponse(content=content, confidence=0.85, provider=self.name, model=self.model, raw=data)


# ---------------------------------------------------------------------------
# Google Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider(BaseModelProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> ModelResponse:
        import httpx

        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}",
            json={
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
                "generationConfig": {"temperature": kwargs.get("temperature", 0.3)},
            },
            timeout=kwargs.get("timeout", 30),
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return ModelResponse(content=content, confidence=0.83, provider=self.name, model=self.model, raw=data)


# ---------------------------------------------------------------------------
# Anthropic Claude provider
# ---------------------------------------------------------------------------

class ClaudeProvider(BaseModelProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> ModelResponse:
        import httpx

        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", 1024),
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=kwargs.get("timeout", 30),
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"]
        return ModelResponse(content=content, confidence=0.88, provider=self.name, model=self.model, raw=data)


# ---------------------------------------------------------------------------
# Model Manager — single entry point for agents
# ---------------------------------------------------------------------------

class ModelManager:
    """Routes model calls to the configured provider.

    Provider is selected via MODEL_PROVIDER env var:
      stub (default) | openai | gemini | claude
    """

    def __init__(self):
        self._provider: BaseModelProvider = None
        self._init_provider()

    def _init_provider(self):
        provider_name = os.environ.get("MODEL_PROVIDER", "stub")
        if provider_name == "openai" and os.environ.get("OPENAI_API_KEY"):
            self._provider = OpenAIProvider(
                os.environ["OPENAI_API_KEY"],
                os.environ.get("MODEL_NAME", "gpt-4o-mini"),
            )
        elif provider_name == "gemini" and os.environ.get("GEMINI_API_KEY"):
            self._provider = GeminiProvider(
                os.environ["GEMINI_API_KEY"],
                os.environ.get("MODEL_NAME", "gemini-1.5-flash"),
            )
        elif provider_name == "claude" and os.environ.get("ANTHROPIC_API_KEY"):
            self._provider = ClaudeProvider(
                os.environ["ANTHROPIC_API_KEY"],
                os.environ.get("MODEL_NAME", "claude-3-5-sonnet-20241022"),
            )
        else:
            logger.info("ModelManager: using stub provider (no API key configured for '%s')", provider_name)
            self._provider = StubProvider()

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> ModelResponse:
        return self._provider.generate(system_prompt, user_prompt, **kwargs)


# Singleton model manager
model_manager = ModelManager()
