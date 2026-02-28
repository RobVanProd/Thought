"""Thread-safe Thought Memory Store with SQLite metadata and hybrid retrieval."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence, TYPE_CHECKING

import numpy as np

from .models import ScoredThought, Thought, ThoughtFilters

if TYPE_CHECKING:
    from .graph import ThoughtGraph


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dt_to_iso(dt: datetime) -> str:
    return _to_utc(dt).isoformat()


def _iso_to_dt(value: str) -> datetime:
    return _to_utc(datetime.fromisoformat(value))


def _vector_to_blob(vector: Sequence[float]) -> bytes:
    arr = np.asarray(vector, dtype=np.float32)
    return arr.tobytes()


def _blob_to_vector(blob: bytes, dim: int) -> list[float]:
    arr = np.frombuffer(blob, dtype=np.float32)
    if arr.size != dim:
        raise ValueError(f"Embedding blob size mismatch. expected={dim}, actual={arr.size}")
    return arr.astype(np.float32).tolist()


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if float(norm) == 0.0:
        return vec
    return vec / norm


class _VectorBackend:
    name = "base"

    def build(self, items: list[tuple[str, list[float]]]) -> None:
        raise NotImplementedError

    def upsert(self, thought_id: str, vector: Sequence[float]) -> None:
        raise NotImplementedError

    def search(self, query_vector: Sequence[float], top_k: int) -> list[tuple[str, float]]:
        raise NotImplementedError


class _NumpyVectorBackend(_VectorBackend):
    name = "numpy"

    def __init__(self, embedding_dim: int) -> None:
        self._embedding_dim = embedding_dim
        self._ids: list[str] = []
        self._id_to_idx: dict[str, int] = {}
        self._size = 0
        self._capacity = 0
        self._matrix = np.zeros((0, embedding_dim), dtype=np.float32)

    def build(self, items: list[tuple[str, list[float]]]) -> None:
        self._ids = [item[0] for item in items]
        self._id_to_idx = {thought_id: idx for idx, thought_id in enumerate(self._ids)}
        if not items:
            self._size = 0
            self._capacity = 0
            self._matrix = np.zeros((0, self._embedding_dim), dtype=np.float32)
            return
        mat = np.asarray([item[1] for item in items], dtype=np.float32)
        if mat.shape[1] != self._embedding_dim:
            raise ValueError(
                f"Vector dimension mismatch while building numpy index. expected={self._embedding_dim}, got={mat.shape[1]}"
            )
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = mat / norms
        self._size = normalized.shape[0]
        self._capacity = max(self._size, 16)
        self._matrix = np.zeros((self._capacity, self._embedding_dim), dtype=np.float32)
        self._matrix[: self._size] = normalized

    def upsert(self, thought_id: str, vector: Sequence[float]) -> None:
        vec = _normalize(np.asarray(vector, dtype=np.float32))
        if vec.shape[0] != self._embedding_dim:
            raise ValueError(
                f"Vector dimension mismatch while upserting numpy index. expected={self._embedding_dim}, got={vec.shape[0]}"
            )
        existing = self._id_to_idx.get(thought_id)
        if existing is not None:
            idx = existing
            self._matrix[idx] = vec
            return
        if self._size >= self._capacity:
            new_capacity = max(16, self._capacity * 2)
            grown = np.zeros((new_capacity, self._embedding_dim), dtype=np.float32)
            if self._size > 0:
                grown[: self._size] = self._matrix[: self._size]
            self._matrix = grown
            self._capacity = new_capacity
        self._matrix[self._size] = vec
        self._id_to_idx[thought_id] = self._size
        self._ids.append(thought_id)
        self._size += 1

    def search(self, query_vector: Sequence[float], top_k: int) -> list[tuple[str, float]]:
        if self._size == 0:
            return []
        q = _normalize(np.asarray(query_vector, dtype=np.float32))
        if q.shape[0] != self._embedding_dim:
            raise ValueError(
                f"query vector dimension {q.shape[0]} does not match embedding_dim {self._embedding_dim}"
            )
        scores = self._matrix[: self._size] @ q
        top_k = max(1, min(top_k, self._size))
        idx = np.argpartition(-scores, top_k - 1)[:top_k]
        ordered = idx[np.argsort(-scores[idx])]
        return [(self._ids[int(i)], float(scores[int(i)])) for i in ordered]


class _FaissVectorBackend(_VectorBackend):
    name = "faiss"

    def __init__(self, embedding_dim: int) -> None:
        try:
            import faiss  # type: ignore
        except Exception as exc:  # pragma: no cover - optional import
            raise RuntimeError("faiss is not installed") from exc
        self._faiss = faiss
        self._embedding_dim = embedding_dim
        self._ids: list[str] = []
        self._index = faiss.IndexFlatIP(embedding_dim)

    def build(self, items: list[tuple[str, list[float]]]) -> None:
        self._ids = [item[0] for item in items]
        self._index.reset()
        if not items:
            return
        mat = np.asarray([item[1] for item in items], dtype=np.float32)
        if mat.shape[1] != self._embedding_dim:
            raise ValueError(
                f"Vector dimension mismatch while building faiss index. expected={self._embedding_dim}, got={mat.shape[1]}"
            )
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._index.add(mat / norms)

    def upsert(self, thought_id: str, vector: Sequence[float]) -> None:
        # Flat faiss index does not support update by id; rebuild is required.
        raise NotImplementedError

    def search(self, query_vector: Sequence[float], top_k: int) -> list[tuple[str, float]]:
        if self._index.ntotal == 0:
            return []
        q = _normalize(np.asarray(query_vector, dtype=np.float32)).reshape(1, -1)
        if q.shape[1] != self._embedding_dim:
            raise ValueError(
                f"query vector dimension {q.shape[1]} does not match embedding_dim {self._embedding_dim}"
            )
        top_k = max(1, min(top_k, self._index.ntotal))
        scores, indices = self._index.search(q, top_k)
        out: list[tuple[str, float]] = []
        for i, score in zip(indices[0], scores[0]):
            if i < 0:
                continue
            out.append((self._ids[int(i)], float(score)))
        return out


class ThoughtStore:
    """SQLite-backed, thread-safe thought store with hybrid semantic retrieval."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        embedding_dim: int = 384,
        vector_backend: str = "auto",
    ) -> None:
        if embedding_dim <= 0:
            raise ValueError("embedding_dim must be positive")
        self.embedding_dim = int(embedding_dim)
        self.db_path = ":memory:" if db_path is None else str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()

        self._vector_backend = self._resolve_vector_backend(vector_backend)
        self._init_schema()
        self._rebuild_vector_index_locked()

    @property
    def vector_backend_name(self) -> str:
        return self._vector_backend.name

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "ThoughtStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _resolve_vector_backend(self, requested: str) -> _VectorBackend:
        key = requested.lower().strip()
        if key not in {"auto", "numpy", "faiss"}:
            raise ValueError("vector_backend must be one of: auto, numpy, faiss")
        if key in {"auto", "faiss"}:
            try:
                return _FaissVectorBackend(self.embedding_dim)
            except Exception:
                if key == "faiss":
                    raise
        return _NumpyVectorBackend(self.embedding_dim)

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    parent_session_id TEXT NULL,
                    created_at_utc TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id)")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS thoughts (
                    id TEXT PRIMARY KEY,
                    timestamp_utc TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    tags_json TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    cleaned_text TEXT NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    embedding_blob BLOB NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_session ON thoughts(session_id)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_category ON thoughts(category)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_confidence ON thoughts(confidence)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_timestamp ON thoughts(timestamp_utc)")
            self._conn.commit()

    def create_session(
        self,
        session_id: str,
        *,
        parent_session_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Create or upsert session hierarchy metadata."""
        if not session_id.strip():
            raise ValueError("session_id must be non-empty")
        with self._lock:
            if parent_session_id is not None and parent_session_id.strip():
                self._conn.execute(
                    """
                    INSERT INTO sessions (session_id, parent_session_id, created_at_utc, metadata_json)
                    VALUES (?, NULL, ?, ?)
                    ON CONFLICT(session_id) DO NOTHING
                    """,
                    (parent_session_id, _dt_to_iso(_utc_now()), json.dumps({})),
                )
            self._conn.execute(
                """
                INSERT INTO sessions (session_id, parent_session_id, created_at_utc, metadata_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    parent_session_id=excluded.parent_session_id,
                    metadata_json=excluded.metadata_json
                """,
                (
                    session_id,
                    parent_session_id,
                    _dt_to_iso(_utc_now()),
                    json.dumps(metadata or {}),
                ),
            )
            self._conn.commit()

    def get_session_parent(self, session_id: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT parent_session_id FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        parent = row["parent_session_id"]
        return None if parent is None else str(parent)

    def get_session_lineage(self, session_id: str, *, include_self: bool = True) -> list[str]:
        """Return ancestor chain for session (self -> parent -> ...)."""
        lineage: list[str] = []
        current = session_id if include_self else self.get_session_parent(session_id)
        visited: set[str] = set()
        while current:
            if current in visited:
                break
            visited.add(current)
            lineage.append(current)
            current = self.get_session_parent(current)
        return lineage

    def _rebuild_vector_index_locked(self) -> None:
        rows = self._conn.execute("SELECT id, embedding_blob, embedding_dim FROM thoughts").fetchall()
        items: list[tuple[str, list[float]]] = []
        for row in rows:
            dim = int(row["embedding_dim"])
            vec = _blob_to_vector(row["embedding_blob"], dim)
            items.append((str(row["id"]), vec))
        self._vector_backend.build(items)

    def store(self, thought: Thought) -> Thought:
        """Store one thought atomically."""
        return self.batch_store([thought])[0]

    def batch_store(self, thoughts: Iterable[Thought]) -> list[Thought]:
        """Store many thoughts atomically in one transaction."""
        thoughts_list = list(thoughts)
        if not thoughts_list:
            return []
        for thought in thoughts_list:
            if thought.embedding_dim != self.embedding_dim:
                raise ValueError(
                    f"Thought embedding_dim={thought.embedding_dim} does not match store embedding_dim={self.embedding_dim}"
                )

        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute("BEGIN")
                for thought in thoughts_list:
                    self._conn.execute(
                        """
                        INSERT INTO sessions (session_id, parent_session_id, created_at_utc, metadata_json)
                        VALUES (?, NULL, ?, ?)
                        ON CONFLICT(session_id) DO NOTHING
                        """,
                        (thought.session_id, _dt_to_iso(_utc_now()), json.dumps({})),
                    )
                    cur.execute(
                        """
                        INSERT INTO thoughts (
                            id, timestamp_utc, session_id, category, confidence, tags_json,
                            raw_text, cleaned_text, embedding_dim, embedding_blob, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            timestamp_utc=excluded.timestamp_utc,
                            session_id=excluded.session_id,
                            category=excluded.category,
                            confidence=excluded.confidence,
                            tags_json=excluded.tags_json,
                            raw_text=excluded.raw_text,
                            cleaned_text=excluded.cleaned_text,
                            embedding_dim=excluded.embedding_dim,
                            embedding_blob=excluded.embedding_blob,
                            payload_json=excluded.payload_json
                        """,
                        (
                            thought.id,
                            _dt_to_iso(thought.timestamp_utc),
                            thought.session_id,
                            thought.category,
                            float(thought.confidence),
                            json.dumps(thought.tags),
                            thought.raw_text,
                            thought.cleaned_text,
                            int(thought.embedding_dim),
                            _vector_to_blob(thought.embedding_vector),
                            thought.model_dump_json(),
                        ),
                    )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

            if isinstance(self._vector_backend, _NumpyVectorBackend):
                for thought in thoughts_list:
                    self._vector_backend.upsert(thought.id, thought.embedding_vector)
            else:
                self._rebuild_vector_index_locked()
        return thoughts_list

    def retrieve(
        self,
        *,
        filters: ThoughtFilters | None = None,
        limit: int = 20,
    ) -> list[Thought]:
        """Retrieve thoughts by metadata filters (no semantic ranking)."""
        filters = filters or ThoughtFilters()
        with self._lock:
            rows = self._query_rows_locked(filters=filters, limit=limit)
        return [self._row_to_thought(row) for row in rows]

    def semantic_search(
        self,
        query_vector: Sequence[float],
        *,
        filters: ThoughtFilters | None = None,
        limit: int = 10,
        alpha: float = 0.9,
        max_candidates: int = 500,
    ) -> list[ScoredThought]:
        """Hybrid search: cosine similarity + metadata filters + mild recency prior."""
        if not (0.0 <= alpha <= 1.0):
            raise ValueError("alpha must be in [0.0, 1.0]")
        filters = filters or ThoughtFilters()
        with self._lock:
            candidates = self._vector_backend.search(query_vector, top_k=max(limit * 10, min(max_candidates, 1000)))
            if not candidates:
                return []
            id_to_score = {thought_id: score for thought_id, score in candidates}
            ids = list(id_to_score.keys())
            rows = self._fetch_rows_by_ids_locked(ids)

        filtered_rows = [row for row in rows if self._row_matches_filters(row, filters)]
        if not filtered_rows:
            return []

        now = _utc_now()
        max_age = 1.0
        ages: list[float] = []
        for row in filtered_rows:
            age = max(0.0, (now - _iso_to_dt(str(row["timestamp_utc"]))).total_seconds())
            ages.append(age)
            max_age = max(max_age, age)

        scored: list[ScoredThought] = []
        for row, age in zip(filtered_rows, ages):
            thought_id = str(row["id"])
            semantic_score = float(id_to_score.get(thought_id, -1.0))
            recency_score = 1.0 - (age / max_age)
            score = alpha * semantic_score + (1.0 - alpha) * recency_score
            scored.append(
                ScoredThought(
                    thought=self._row_to_thought(row),
                    semantic_score=semantic_score,
                    recency_score=recency_score,
                    score=score,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: max(1, limit)]

    def recall_from_prior_sessions(
        self,
        query_vector: Sequence[float],
        *,
        current_session_id: str,
        graph: "ThoughtGraph | None" = None,
        limit: int = 10,
        alpha: float = 0.9,
        graph_hops: int = 1,
    ) -> list[ScoredThought]:
        """Recall relevant thoughts from ancestor sessions using semantic + graph expansion."""
        lineage = self.get_session_lineage(current_session_id, include_self=False)
        if not lineage:
            return []
        lineage_set = set(lineage)
        semantic = self.semantic_search(query_vector, limit=max(30, limit * 4), alpha=alpha)
        semantic = [item for item in semantic if item.thought.session_id in lineage_set]

        if graph is None or graph_hops <= 0:
            return semantic[:limit]

        expanded: dict[str, ScoredThought] = {item.thought.id: item for item in semantic}
        for item in list(semantic[:5]):
            neighbors = graph.neighbors(item.thought.id, hops=graph_hops, limit=25)
            for n_id in neighbors:
                if n_id in expanded:
                    continue
                thought = self.get_thought_by_id(n_id)
                if thought is None or thought.session_id not in lineage_set:
                    continue
                expanded[n_id] = ScoredThought(
                    thought=thought,
                    semantic_score=item.semantic_score * 0.85,
                    recency_score=item.recency_score,
                    score=item.score * 0.85,
                )

        out = sorted(expanded.values(), key=lambda x: x.score, reverse=True)
        return out[:limit]

    def get_thought_by_id(self, thought_id: str) -> Thought | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM thoughts WHERE id = ?", (thought_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_thought(row)

    async def astore(self, thought: Thought) -> Thought:
        return await asyncio.to_thread(self.store, thought)

    async def abatch_store(self, thoughts: Iterable[Thought]) -> list[Thought]:
        return await asyncio.to_thread(self.batch_store, list(thoughts))

    async def aretrieve(self, *, filters: ThoughtFilters | None = None, limit: int = 20) -> list[Thought]:
        return await asyncio.to_thread(self.retrieve, filters=filters, limit=limit)

    async def asemantic_search(
        self,
        query_vector: Sequence[float],
        *,
        filters: ThoughtFilters | None = None,
        limit: int = 10,
        alpha: float = 0.9,
        max_candidates: int = 500,
    ) -> list[ScoredThought]:
        return await asyncio.to_thread(
            self.semantic_search,
            query_vector,
            filters=filters,
            limit=limit,
            alpha=alpha,
            max_candidates=max_candidates,
        )

    async def arecall_from_prior_sessions(
        self,
        query_vector: Sequence[float],
        *,
        current_session_id: str,
        graph: "ThoughtGraph | None" = None,
        limit: int = 10,
        alpha: float = 0.9,
        graph_hops: int = 1,
    ) -> list[ScoredThought]:
        return await asyncio.to_thread(
            self.recall_from_prior_sessions,
            query_vector,
            current_session_id=current_session_id,
            graph=graph,
            limit=limit,
            alpha=alpha,
            graph_hops=graph_hops,
        )

    def _query_rows_locked(self, *, filters: ThoughtFilters, limit: int) -> list[sqlite3.Row]:
        clauses = ["1=1"]
        params: list[object] = []

        if filters.session_id is not None:
            clauses.append("session_id = ?")
            params.append(filters.session_id)
        if filters.category is not None:
            clauses.append("category = ?")
            params.append(filters.category)
        if filters.min_confidence is not None:
            clauses.append("confidence >= ?")
            params.append(float(filters.min_confidence))
        if filters.start_time_utc is not None:
            clauses.append("timestamp_utc >= ?")
            params.append(_dt_to_iso(filters.start_time_utc))
        if filters.end_time_utc is not None:
            clauses.append("timestamp_utc <= ?")
            params.append(_dt_to_iso(filters.end_time_utc))

        sql = f"SELECT * FROM thoughts WHERE {' AND '.join(clauses)} ORDER BY timestamp_utc DESC LIMIT ?"
        params.append(max(1, limit))
        rows = self._conn.execute(sql, params).fetchall()
        if filters.tags_any:
            tags_filter = set(filters.tags_any)
            rows = [row for row in rows if tags_filter.intersection(set(json.loads(row["tags_json"])))]
        return rows

    def _fetch_rows_by_ids_locked(self, ids: list[str]) -> list[sqlite3.Row]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(f"SELECT * FROM thoughts WHERE id IN ({placeholders})", ids).fetchall()
        return rows

    def _row_matches_filters(self, row: sqlite3.Row, filters: ThoughtFilters) -> bool:
        if filters.session_id is not None and str(row["session_id"]) != filters.session_id:
            return False
        if filters.category is not None and str(row["category"]) != filters.category:
            return False
        if filters.min_confidence is not None and float(row["confidence"]) < float(filters.min_confidence):
            return False
        row_dt = _iso_to_dt(str(row["timestamp_utc"]))
        if filters.start_time_utc is not None and row_dt < _to_utc(filters.start_time_utc):
            return False
        if filters.end_time_utc is not None and row_dt > _to_utc(filters.end_time_utc):
            return False
        if filters.tags_any:
            tags = set(json.loads(row["tags_json"]))
            if not tags.intersection(set(filters.tags_any)):
                return False
        return True

    @staticmethod
    def _row_to_thought(row: sqlite3.Row) -> Thought:
        return Thought(
            id=str(row["id"]),
            timestamp_utc=_iso_to_dt(str(row["timestamp_utc"])),
            session_id=str(row["session_id"]),
            category=str(row["category"]),
            confidence=float(row["confidence"]),
            tags=list(json.loads(row["tags_json"])),
            raw_text=str(row["raw_text"]),
            cleaned_text=str(row["cleaned_text"]),
            embedding_dim=int(row["embedding_dim"]),
            embedding_vector=_blob_to_vector(row["embedding_blob"], int(row["embedding_dim"])),
        )
