"""Reflection engine for generating and storing meta-thoughts."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
from uuid import uuid4

from .embeddings import Embedder, resolve_embedder
from .graph import ThoughtGraph
from .models import ReflectionResult, Thought, ThoughtFilters
from .prompt_helpers import REFLECTION_TEMPLATES, build_reflection_prompt
from .store import ThoughtStore


_THOUGHT_PATTERN = re.compile(r"<thought\b([^>]*)>(.*?)</thought>", flags=re.IGNORECASE | re.DOTALL)
_ATTR_PATTERN = re.compile(r'(\w+)\s*=\s*"([^"]*?)"')


@dataclass(frozen=True)
class ParsedStructuredThought:
    thought_id: str
    category: str
    confidence: float
    content: str


def parse_structured_thoughts(
    text: str,
    *,
    default_category: str = "reflection",
    default_confidence: float = 0.9,
) -> list[ParsedStructuredThought]:
    """Parse <thought ...>content</thought> tags into structured units."""
    out: list[ParsedStructuredThought] = []
    for match in _THOUGHT_PATTERN.finditer(text):
        attrs_raw = match.group(1) or ""
        content = (match.group(2) or "").strip()
        if not content:
            continue
        attrs = {k.lower(): v for k, v in _ATTR_PATTERN.findall(attrs_raw)}
        thought_id = attrs.get("id", str(uuid4()))
        category = attrs.get("category", default_category).strip() or default_category
        try:
            confidence = float(attrs.get("confidence", str(default_confidence)))
        except ValueError:
            confidence = default_confidence
        confidence = max(0.0, min(1.0, confidence))
        out.append(
            ParsedStructuredThought(
                thought_id=thought_id,
                category=category,
                confidence=confidence,
                content=content,
            )
        )
    return out


class ReflectionEngine:
    """Retrieve memory, synthesize reflections, and store meta-thoughts atomically."""

    def __init__(
        self,
        store: ThoughtStore,
        *,
        graph: ThoughtGraph | None = None,
        embedder: Embedder | None = None,
        embedding_dim: int = 384,
    ) -> None:
        self.store = store
        self.graph = graph
        self.embedder = resolve_embedder(embedder, dimension=embedding_dim)

    def reflect(
        self,
        *,
        query: str,
        current_session_id: str,
        mode: str = "reasoning",
        top_k: int = 8,
        reflection_session_id: str | None = None,
        llm_callable: Callable[[str], str] | None = None,
    ) -> ReflectionResult:
        """Run one reflection cycle and persist generated meta-thoughts."""
        if mode not in REFLECTION_TEMPLATES:
            raise ValueError(f"Unsupported reflection mode: {mode}")
        start = time.perf_counter()

        query_vector = self.embedder.embed(query)
        current_hits = self.store.semantic_search(
            query_vector,
            filters=ThoughtFilters(session_id=current_session_id),
            limit=top_k,
            alpha=0.95,
        )
        prior_hits = self.store.recall_from_prior_sessions(
            query_vector,
            current_session_id=current_session_id,
            graph=self.graph,
            limit=top_k,
            alpha=0.95,
            graph_hops=1,
        )

        merged: dict[str, Thought] = {}
        for hit in current_hits + prior_hits:
            merged[hit.thought.id] = hit.thought
        recalled = list(merged.values())[: max(1, top_k)]
        context = "\n".join(
            f"- ({t.session_id}/{t.category}/{t.confidence:.2f}) {t.cleaned_text}"
            for t in recalled
        ) or "- (none)"
        prompt = build_reflection_prompt(mode, query, context)

        if llm_callable is None:
            reflection_text = self._default_reflection_text(mode=mode, query=query, recalled=recalled)
        else:
            reflection_text = llm_callable(prompt)

        parsed = parse_structured_thoughts(
            reflection_text,
            default_category="reflection" if mode != "planning" else "plan",
            default_confidence=0.9,
        )
        session_id = reflection_session_id or current_session_id
        if reflection_session_id and reflection_session_id != current_session_id:
            self.store.create_session(reflection_session_id, parent_session_id=current_session_id)
        else:
            self.store.create_session(current_session_id)

        to_store: list[Thought] = []
        for item in parsed:
            vector = self.embedder.embed(item.content)
            to_store.append(
                Thought(
                    id=item.thought_id,
                    session_id=session_id,
                    category=item.category,
                    confidence=item.confidence,
                    tags=["reflection", mode],
                    raw_text=item.content,
                    cleaned_text=item.content,
                    embedding_vector=vector,
                    embedding_dim=len(vector),
                )
            )

        stored = self.store.batch_store(to_store) if to_store else []
        if self.graph is not None:
            pending_edges: list[tuple[str, str, str, float, dict[str, object]]] = []
            for t in stored:
                self.graph.add_thought(t, store_if_missing=False, semantic_neighbors=0, temporal_link=True)
                for recalled_thought in recalled[:1]:
                    pending_edges.append(
                        (
                            recalled_thought.id,
                            t.id,
                            "explicit-reference",
                            1.0,
                            {"mode": mode},
                        )
                    )
            if pending_edges:
                self.graph.link_many(pending_edges)

        latency_ms = (time.perf_counter() - start) * 1000.0
        return ReflectionResult(
            reflection_text=reflection_text,
            prompt_used=prompt,
            recalled_thoughts=recalled,
            stored_reflections=stored,
            latency_ms=latency_ms,
        )

    async def areflect(self, **kwargs) -> ReflectionResult:
        return await asyncio.to_thread(self.reflect, **kwargs)

    @staticmethod
    def _default_reflection_text(mode: str, query: str, recalled: Sequence[Thought]) -> str:
        if recalled:
            first = recalled[0].cleaned_text
            second = recalled[1].cleaned_text if len(recalled) > 1 else recalled[0].cleaned_text
        else:
            first = f"No prior memory for query: {query}"
            second = "Need additional evidence before confidence increases."

        if mode == "summarization":
            return (
                f'<thought id="{uuid4()}" category="summary" confidence="0.93">'
                f"Summary memory: {first}"
                "</thought>\n"
                f'<thought id="{uuid4()}" category="summary" confidence="0.88">'
                f"Actionable summary: {second}"
                "</thought>"
            )
        if mode == "contradiction_detection":
            return (
                f'<thought id="{uuid4()}" category="reflection" confidence="0.91">'
                f"Potential contradiction check: {first}"
                "</thought>\n"
                f'<thought id="{uuid4()}" category="reflection" confidence="0.86">'
                f"Reconciliation candidate: {second}"
                "</thought>"
            )
        if mode == "planning":
            return (
                f'<thought id="{uuid4()}" category="plan" confidence="0.92">'
                f"Next step: operationalize {first}"
                "</thought>\n"
                f'<thought id="{uuid4()}" category="plan" confidence="0.87">'
                f"Validation step: verify against {second}"
                "</thought>"
            )
        # reasoning default
        return (
            f'<thought id="{uuid4()}" category="reflection" confidence="0.94">'
            f"Reasoning check: {first}"
            "</thought>\n"
            f'<thought id="{uuid4()}" category="reflection" confidence="0.89">'
            f"Risk note: {second}"
            "</thought>"
        )
