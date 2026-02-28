"""Pydantic models for Thought Memory System entities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Thought(BaseModel):
    """Canonical thought record persisted by the TMS."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp_utc: datetime = Field(default_factory=utc_now)
    session_id: str = Field(min_length=1)
    category: str = Field(default="reasoning", min_length=1)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    raw_text: str = Field(min_length=1)
    cleaned_text: str = Field(min_length=1)
    embedding_vector: List[float] = Field(min_length=1)
    embedding_dim: Optional[int] = None

    @model_validator(mode="after")
    def _validate_embedding(self) -> "Thought":
        if self.embedding_dim is None:
            self.embedding_dim = len(self.embedding_vector)
        if self.embedding_dim <= 0:
            raise ValueError("embedding_dim must be positive")
        if len(self.embedding_vector) != self.embedding_dim:
            raise ValueError(
                f"embedding_vector length ({len(self.embedding_vector)}) does not match embedding_dim ({self.embedding_dim})"
            )
        return self


class ThoughtFilters(BaseModel):
    """Metadata filters for retrieval/search operations."""

    model_config = ConfigDict(extra="forbid")

    session_id: Optional[str] = None
    category: Optional[str] = None
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    start_time_utc: Optional[datetime] = None
    end_time_utc: Optional[datetime] = None
    tags_any: Optional[List[str]] = None


class ScoredThought(BaseModel):
    """Thought paired with similarity and hybrid rank score."""

    thought: Thought
    semantic_score: float
    recency_score: float = 0.0
    score: float


class ParseStoreResult(BaseModel):
    """Pipeline output after parse+embed+store."""

    cleaned_output: str
    thoughts: List[Thought]
    used_linear_fallback: bool = False


class ReflectionResult(BaseModel):
    """Output of a reflection cycle."""

    reflection_text: str
    prompt_used: str
    recalled_thoughts: List[Thought]
    stored_reflections: List[Thought]
    latency_ms: float
