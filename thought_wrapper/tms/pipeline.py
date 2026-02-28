"""Parse -> embed -> store pipeline for TMS ingestion."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Sequence

from thought_wrapper.core import (
    clean_thought_tags,
    clean_thought_tags_linear,
    parse_thought_tags,
    parse_thought_tags_linear,
)

from .embeddings import Embedder, resolve_embedder
from .models import ParseStoreResult, Thought
from .store import ThoughtStore


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_and_store(
    raw_output: str,
    store: ThoughtStore,
    *,
    session_id: str,
    category: str = "reasoning",
    confidence: float = 0.9,
    tags: Sequence[str] | None = None,
    tag_name: str = "thought",
    linear_fallback: bool = True,
    embedder: Embedder | None = None,
    embedding_dim: int = 384,
) -> ParseStoreResult:
    """Atomically parse tagged output, embed each thought, and persist."""
    if not session_id.strip():
        raise ValueError("session_id must be non-empty")

    regex_thoughts = parse_thought_tags(raw_output, tag_name=tag_name)
    thoughts_map = regex_thoughts
    cleaned_output = clean_thought_tags(raw_output, tag_name=tag_name)
    used_linear_fallback = False

    if linear_fallback:
        linear_thoughts = parse_thought_tags_linear(raw_output, tag_name=tag_name)
        # Prefer linear parse when it captures additional content (e.g., nested brackets).
        should_use_linear = len(linear_thoughts) > len(regex_thoughts)
        if not should_use_linear and linear_thoughts:
            for key, linear_content in linear_thoughts.items():
                regex_content = regex_thoughts.get(key, "")
                if len(linear_content) > len(regex_content):
                    should_use_linear = True
                    break

        if should_use_linear:
            thoughts_map = linear_thoughts
            cleaned_output = clean_thought_tags_linear(raw_output, tag_name=tag_name)
            used_linear_fallback = True

    resolved_embedder = resolve_embedder(embedder, dimension=embedding_dim)
    thought_objects: list[Thought] = []
    common_tags = list(tags or [])
    now = _utc_now()

    for _, content in thoughts_map.items():
        clean_content = content.strip()
        vector = resolved_embedder.embed(clean_content)
        thought_objects.append(
            Thought(
                timestamp_utc=now,
                session_id=session_id,
                category=category,
                confidence=confidence,
                tags=common_tags,
                raw_text=content,
                cleaned_text=clean_content,
                embedding_vector=vector,
                embedding_dim=len(vector),
            )
        )

    if thought_objects:
        # Atomic batch write; no partial persistence if insertion fails.
        store.batch_store(thought_objects)

    return ParseStoreResult(
        cleaned_output=cleaned_output,
        thoughts=thought_objects,
        used_linear_fallback=used_linear_fallback,
    )


async def aparse_and_store(
    raw_output: str,
    store: ThoughtStore,
    *,
    session_id: str,
    category: str = "reasoning",
    confidence: float = 0.9,
    tags: Sequence[str] | None = None,
    tag_name: str = "thought",
    linear_fallback: bool = True,
    embedder: Embedder | None = None,
    embedding_dim: int = 384,
) -> ParseStoreResult:
    """Async wrapper for parse_and_store."""
    return await asyncio.to_thread(
        parse_and_store,
        raw_output,
        store,
        session_id=session_id,
        category=category,
        confidence=confidence,
        tags=tags,
        tag_name=tag_name,
        linear_fallback=linear_fallback,
        embedder=embedder,
        embedding_dim=embedding_dim,
    )
