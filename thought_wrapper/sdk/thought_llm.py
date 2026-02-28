"""Unified ThoughtLLM orchestrator for multi-model completion + memory + reflection."""

from __future__ import annotations

import asyncio
import re
import threading
import time
from dataclasses import dataclass
from typing import Sequence

from thought_wrapper.tms import (
    HashEmbedder,
    ReflectionEngine,
    Thought,
    ThoughtGraph,
    ThoughtStore,
    parse_and_store,
    parse_structured_thoughts,
)
from thought_wrapper.tms.prompt_helpers import SYSTEM_PROMPT_CODEX3, THOUGHT_TAG_GUIDANCE

from .clients import LLMClient
from .models import ThoughtCompletionResult, ThoughtLLMConfig


_XML_THOUGHT_RE = re.compile(r"<thought\b[^>]*>.*?</thought>", flags=re.IGNORECASE | re.DOTALL)


def _strip_xml_thought_tags(text: str) -> str:
    cleaned = _XML_THOUGHT_RE.sub("\n", text)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


@dataclass
class ThoughtLLM:
    """Unified model client that injects thought prompts and auto-persists memory."""

    client: LLMClient
    store: ThoughtStore
    graph: ThoughtGraph
    reflection_engine: ReflectionEngine
    config: ThoughtLLMConfig
    embedder: HashEmbedder

    def __init__(
        self,
        client: LLMClient,
        *,
        store: ThoughtStore,
        graph: ThoughtGraph | None = None,
        reflection_engine: ReflectionEngine | None = None,
        config: ThoughtLLMConfig,
        embedder: HashEmbedder | None = None,
    ) -> None:
        self.client = client
        self.store = store
        self.graph = graph or ThoughtGraph(store)
        self.embedder = embedder or HashEmbedder(dimension=store.embedding_dim)
        self.reflection_engine = reflection_engine or ReflectionEngine(
            store,
            graph=self.graph,
            embedder=self.embedder,
            embedding_dim=store.embedding_dim,
        )
        self.config = config
        self._calls = 0
        self._lock = threading.RLock()

    def complete(
        self,
        user_prompt: str,
        *,
        session_id: str,
        parent_session_id: str | None = None,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        category: str = "reasoning",
        tags: Sequence[str] | None = None,
        reflect: bool | None = None,
        reflection_mode: str | None = None,
        thought_tagging_enforcement: str | None = None,
        recall_top_k: int | None = None,
    ) -> ThoughtCompletionResult:
        """Run model completion and integrate output into thought memory."""
        if not session_id.strip():
            raise ValueError("session_id must be non-empty")

        with self._lock:
            self._calls += 1
            call_index = self._calls

        if parent_session_id:
            self.store.create_session(session_id, parent_session_id=parent_session_id)
        else:
            self.store.create_session(session_id)

        recall_k = recall_top_k or self.config.recall_top_k
        query_vec = self.embedder.embed(user_prompt)
        current_hits = self.store.semantic_search(
            query_vec,
            filters=None,
            limit=recall_k,
            alpha=0.95,
        )
        prior_hits = self.store.recall_from_prior_sessions(
            query_vec,
            current_session_id=session_id,
            graph=self.graph,
            limit=recall_k,
            alpha=0.95,
            graph_hops=1,
        )

        merged: dict[str, Thought] = {}
        for hit in current_hits + prior_hits:
            merged[hit.thought.id] = hit.thought
        recalled = list(merged.values())[:recall_k]
        recall_context = "\n".join(
            f"- ({t.session_id}/{t.category}/{t.confidence:.2f}) {t.cleaned_text}" for t in recalled
        )

        enforcement = thought_tagging_enforcement or self.config.thought_tagging_enforcement
        default_system = system_prompt or SYSTEM_PROMPT_CODEX3
        if enforcement == "xml":
            enforced = (
                default_system
                + "\n"
                + THOUGHT_TAG_GUIDANCE
                + "\nUse only XML <thought ...> tags for intermediate reasoning."
            )
        elif enforcement == "slash":
            enforced = (
                default_system
                + "\nFor intermediate reasoning, use /thought[...] tags. Keep final answer outside those tags."
            )
        else:
            enforced = default_system + "\nPrefer XML <thought> tags; /thought[...] is acceptable fallback."

        final_user_prompt = user_prompt
        if recall_context:
            final_user_prompt = (
                f"{user_prompt}\n\nRecalled memory context:\n{recall_context}\n"
                "Use relevant context; add new thought tags for new reasoning."
            )

        start = time.perf_counter()
        raw_output = self.client.complete(
            system_prompt=enforced,
            user_prompt=final_user_prompt,
            model=model or self.config.model,
            temperature=self.config.temperature if temperature is None else temperature,
            max_tokens=self.config.max_tokens if max_tokens is None else max_tokens,
        )

        cleaned_output, stored_thoughts = self._ingest_output(
            raw_output,
            session_id=session_id,
            category=category,
            tags=list(tags or []),
            enforcement=enforcement,
        )

        for thought in stored_thoughts:
            self.graph.add_thought(thought, store_if_missing=False, semantic_neighbors=0, temporal_link=True)

        do_reflect = self.config.reflect_enabled if reflect is None else reflect
        reflection = None
        if do_reflect and self.config.reflection_frequency > 0 and (call_index % self.config.reflection_frequency == 0):
            reflection = self.reflection_engine.reflect(
                query=user_prompt,
                current_session_id=session_id,
                mode=reflection_mode or self.config.reflection_mode,
                top_k=recall_k,
            )

        latency_ms = (time.perf_counter() - start) * 1000.0
        return ThoughtCompletionResult(
            raw_output=raw_output,
            cleaned_output=cleaned_output,
            stored_thoughts=stored_thoughts,
            recalled_context=recalled,
            reflection=reflection,
            model_name=model or self.config.model,
            provider=self.client.provider_name,
            latency_ms=latency_ms,
            prompt_used=enforced,
        )

    async def acomplete(self, *args, **kwargs) -> ThoughtCompletionResult:
        return await asyncio.to_thread(self.complete, *args, **kwargs)

    def _ingest_output(
        self,
        raw_output: str,
        *,
        session_id: str,
        category: str,
        tags: list[str],
        enforcement: str,
    ) -> tuple[str, list[Thought]]:
        parsed_xml = parse_structured_thoughts(raw_output)
        use_xml = enforcement == "xml" or (enforcement == "auto" and bool(parsed_xml))

        if use_xml and parsed_xml:
            thoughts: list[Thought] = []
            for item in parsed_xml:
                content = item.content.strip()
                vec = self.embedder.embed(content)
                thoughts.append(
                    Thought(
                        id=item.thought_id,
                        session_id=session_id,
                        category=item.category or category,
                        confidence=item.confidence,
                        tags=list(tags),
                        raw_text=item.content,
                        cleaned_text=content,
                        embedding_vector=vec,
                        embedding_dim=len(vec),
                    )
                )
            if thoughts:
                self.store.batch_store(thoughts)
            return _strip_xml_thought_tags(raw_output), thoughts

        parsed = parse_and_store(
            raw_output,
            self.store,
            session_id=session_id,
            category=category,
            confidence=0.9,
            tags=tags,
            tag_name="thought",
            linear_fallback=True,
            embedder=self.embedder,
            embedding_dim=self.embedder.dimension,
        )
        return parsed.cleaned_output, parsed.thoughts
