"""FastAPI memory service for TMS/Graph/Reflection endpoints."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from thought_wrapper.tms import HashEmbedder, ReflectionEngine, ThoughtFilters, ThoughtGraph, ThoughtStore
from thought_wrapper.tms.pipeline import parse_and_store

try:
    from fastapi import FastAPI, HTTPException
except Exception as exc:  # pragma: no cover - optional runtime dependency
    raise RuntimeError(
        "FastAPI is not installed. Install `fastapi` and `uvicorn` to run memory_service.py"
    ) from exc


DB_PATH = os.getenv("THOUGHT_DB_PATH", "results/tms_service.sqlite")
EMBED_DIM = int(os.getenv("THOUGHT_EMBED_DIM", "384"))

store = ThoughtStore(db_path=DB_PATH, embedding_dim=EMBED_DIM, vector_backend="auto")
graph = ThoughtGraph(store)
embedder = HashEmbedder(dimension=EMBED_DIM)
reflection_engine = ReflectionEngine(store, graph=graph, embedder=embedder, embedding_dim=EMBED_DIM)

app = FastAPI(title="Thought Memory Service", version="1.0.0")


class StoreRequest(BaseModel):
    raw_output: str
    session_id: str
    category: str = "reasoning"
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class RetrieveRequest(BaseModel):
    query: str
    session_id: str | None = None
    category: str | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=100)


class ReflectRequest(BaseModel):
    query: str
    current_session_id: str
    mode: str = "reasoning"
    top_k: int = Field(default=8, ge=1, le=50)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "timestamp_utc": datetime.utcnow().isoformat() + "Z"}


@app.post("/store")
def store_endpoint(req: StoreRequest) -> dict[str, Any]:
    try:
        parsed = parse_and_store(
            req.raw_output,
            store,
            session_id=req.session_id,
            category=req.category,
            confidence=req.confidence,
            tags=req.tags,
            embedder=embedder,
            embedding_dim=EMBED_DIM,
        )
        for thought in parsed.thoughts:
            graph.add_thought(thought, store_if_missing=False, semantic_neighbors=0, temporal_link=True)
        return {
            "cleaned_output": parsed.cleaned_output,
            "stored_count": len(parsed.thoughts),
            "used_linear_fallback": parsed.used_linear_fallback,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/retrieve")
def retrieve_endpoint(req: RetrieveRequest) -> dict[str, Any]:
    try:
        query_vec = embedder.embed(req.query)
        filters = ThoughtFilters(
            session_id=req.session_id,
            category=req.category,
            min_confidence=req.min_confidence,
        )
        hits = store.semantic_search(query_vec, filters=filters, limit=req.limit, alpha=0.95)
        return {
            "count": len(hits),
            "items": [
                {
                    "id": h.thought.id,
                    "session_id": h.thought.session_id,
                    "category": h.thought.category,
                    "confidence": h.thought.confidence,
                    "text": h.thought.cleaned_text,
                    "score": h.score,
                }
                for h in hits
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/reflect")
def reflect_endpoint(req: ReflectRequest) -> dict[str, Any]:
    try:
        result = reflection_engine.reflect(
            query=req.query,
            current_session_id=req.current_session_id,
            mode=req.mode,
            top_k=req.top_k,
        )
        return {
            "stored_reflections": len(result.stored_reflections),
            "latency_ms": result.latency_ms,
            "reflection_text": result.reflection_text,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/graph/paths")
def graph_paths(source_id: str, target_id: str, max_depth: int = 4, limit: int = 10) -> dict[str, Any]:
    try:
        paths = graph.find_paths(source_id, target_id, max_depth=max_depth, limit=limit)
        return {"count": len(paths), "paths": paths}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

