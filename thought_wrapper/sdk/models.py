"""Data models for SDK-level multi-model integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from thought_wrapper.tms.models import ReflectionResult, Thought


Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass
class ThoughtCompletionResult:
    """Unified completion result from ThoughtLLM."""

    raw_output: str
    cleaned_output: str
    stored_thoughts: list[Thought] = field(default_factory=list)
    recalled_context: list[Thought] = field(default_factory=list)
    reflection: ReflectionResult | None = None
    model_name: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    prompt_used: str = ""


@dataclass
class ThoughtLLMConfig:
    """Configuration for ThoughtLLM orchestration behavior."""

    model: str
    temperature: float = 0.2
    max_tokens: int = 1024
    thought_tagging_enforcement: Literal["xml", "slash", "auto"] = "xml"
    reflection_frequency: int = 1
    reflect_enabled: bool = True
    recall_top_k: int = 8
    reflection_mode: Literal["reasoning", "summarization", "contradiction_detection", "planning"] = "reasoning"

