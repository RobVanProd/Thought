"""ThoughtGraph: directed thought links with SQLite persistence and analytics backends."""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Literal, Sequence

from .models import Thought
from .store import ThoughtStore, _dt_to_iso, _iso_to_dt

RelationType = Literal["semantic-similarity", "explicit-reference", "temporal-successor"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ThoughtEdge:
    source_id: str
    target_id: str
    relation: str
    weight: float
    created_at_utc: datetime
    metadata: dict[str, object]


class ThoughtGraph:
    """Directed thought graph persisted in SQLite with optional analytic backends."""

    def __init__(self, store: ThoughtStore) -> None:
        self._store = store
        self._conn = store._conn  # Shared DB source of truth.
        self._lock = store._lock
        self._backend_name = "builtin"
        self._nx = None
        self._igraph = None
        self._graph_backend = None
        self._igraph_name_to_idx: dict[str, int] = {}
        self._init_schema()
        self._init_backend()
        self._rebuild_backend_locked()

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS thought_graph_nodes (
                    thought_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS thought_graph_edges (
                    edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON thought_graph_edges(source_id)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON thought_graph_edges(target_id)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_relation ON thought_graph_edges(relation)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_session ON thought_graph_nodes(session_id)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_time ON thought_graph_nodes(timestamp_utc)")
            self._conn.commit()

    def _init_backend(self) -> None:
        try:  # Prefer networkx.
            import networkx as nx  # type: ignore

            self._nx = nx
            self._graph_backend = nx.DiGraph()
            self._backend_name = "networkx"
            return
        except Exception:
            pass

        try:  # Fallback to igraph.
            import igraph as ig  # type: ignore

            self._igraph = ig
            self._graph_backend = ig.Graph(directed=True)
            self._backend_name = "igraph"
            return
        except Exception:
            self._backend_name = "builtin"
            self._graph_backend = None

    def _rebuild_backend_locked(self) -> None:
        rows_nodes = self._conn.execute("SELECT thought_id FROM thought_graph_nodes").fetchall()
        rows_edges = self._conn.execute(
            "SELECT source_id, target_id, relation, weight FROM thought_graph_edges"
        ).fetchall()

        if self._backend_name == "networkx":
            graph = self._nx.DiGraph()
            for row in rows_nodes:
                graph.add_node(str(row["thought_id"]))
            for row in rows_edges:
                graph.add_edge(
                    str(row["source_id"]),
                    str(row["target_id"]),
                    relation=str(row["relation"]),
                    weight=float(row["weight"]),
                )
            self._graph_backend = graph
            return

        if self._backend_name == "igraph":
            graph = self._igraph.Graph(directed=True)
            nodes = [str(row["thought_id"]) for row in rows_nodes]
            graph.add_vertices(nodes)
            name_to_idx = {name: idx for idx, name in enumerate(nodes)}
            edges = []
            rels = []
            weights = []
            for row in rows_edges:
                src = str(row["source_id"])
                tgt = str(row["target_id"])
                if src in name_to_idx and tgt in name_to_idx:
                    edges.append((name_to_idx[src], name_to_idx[tgt]))
                    rels.append(str(row["relation"]))
                    weights.append(float(row["weight"]))
            if edges:
                graph.add_edges(edges)
                graph.es["relation"] = rels
                graph.es["weight"] = weights
            self._graph_backend = graph
            self._igraph_name_to_idx = name_to_idx

    def _backend_add_node_locked(self, thought_id: str) -> None:
        if self._backend_name == "networkx":
            self._graph_backend.add_node(thought_id)
            return
        if self._backend_name == "igraph":
            if thought_id in self._igraph_name_to_idx:
                return
            self._graph_backend.add_vertex(name=thought_id)
            self._igraph_name_to_idx[thought_id] = self._graph_backend.vcount() - 1

    def _backend_add_edge_locked(self, source_id: str, target_id: str, relation: str, weight: float) -> None:
        if self._backend_name == "networkx":
            self._graph_backend.add_edge(source_id, target_id, relation=relation, weight=weight)
            return
        if self._backend_name == "igraph":
            self._backend_add_node_locked(source_id)
            self._backend_add_node_locked(target_id)
            self._graph_backend.add_edge(
                self._igraph_name_to_idx[source_id],
                self._igraph_name_to_idx[target_id],
                relation=relation,
                weight=weight,
            )

    def add_thought(
        self,
        thought: Thought,
        *,
        store_if_missing: bool = True,
        semantic_neighbors: int = 3,
        semantic_threshold: float = 0.80,
        temporal_link: bool = True,
    ) -> Thought:
        """Add node to graph, optionally inserting semantic and temporal links."""
        if store_if_missing and self._store.get_thought_by_id(thought.id) is None:
            self._store.store(thought)

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO thought_graph_nodes (thought_id, session_id, timestamp_utc, metadata_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(thought_id) DO UPDATE SET
                    session_id=excluded.session_id,
                    timestamp_utc=excluded.timestamp_utc
                """,
                (
                    thought.id,
                    thought.session_id,
                    _dt_to_iso(thought.timestamp_utc),
                    json.dumps({}),
                ),
            )
            self._conn.commit()
            self._backend_add_node_locked(thought.id)

        if temporal_link:
            self._link_temporal_successor(thought)

        if semantic_neighbors > 0:
            nearest = self._store.semantic_search(thought.embedding_vector, limit=semantic_neighbors + 5, alpha=1.0)
            for item in nearest:
                other = item.thought
                if other.id == thought.id:
                    continue
                if item.semantic_score < semantic_threshold:
                    continue
                self.link(
                    other.id,
                    thought.id,
                    relation="semantic-similarity",
                    weight=float(item.semantic_score),
                )
        return thought

    def _link_temporal_successor(self, thought: Thought) -> None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT thought_id, timestamp_utc
                FROM thought_graph_nodes
                WHERE session_id = ? AND thought_id != ? AND timestamp_utc <= ?
                ORDER BY timestamp_utc DESC
                LIMIT 1
                """,
                (thought.session_id, thought.id, _dt_to_iso(thought.timestamp_utc)),
            ).fetchone()
        if row is None:
            return
        self.link(
            str(row["thought_id"]),
            thought.id,
            relation="temporal-successor",
            weight=1.0,
        )

    def link(
        self,
        source_id: str,
        target_id: str,
        *,
        relation: RelationType | str,
        weight: float = 1.0,
        metadata: dict[str, object] | None = None,
        bidirectional: bool = False,
    ) -> None:
        """Create directed edge(s) between thoughts."""
        if not source_id or not target_id:
            raise ValueError("source_id and target_id must be non-empty")
        if source_id == target_id:
            return
        if weight < 0:
            raise ValueError("weight must be non-negative")
        edges: list[tuple[str, str, str, float, dict[str, object]]] = [
            (source_id, target_id, str(relation), float(weight), metadata or {})
        ]
        if bidirectional:
            edges.append((target_id, source_id, str(relation), float(weight), metadata or {}))
        self.link_many(edges)

    def link_many(self, edges: Sequence[tuple[str, str, str, float, dict[str, object]]]) -> None:
        """Insert many edges atomically with one transaction."""
        if not edges:
            return
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute("BEGIN")
                for source_id, target_id, relation, weight, metadata in edges:
                    if source_id == target_id:
                        continue
                    cur.execute(
                        """
                        INSERT INTO thought_graph_edges (
                            source_id, target_id, relation, weight, created_at_utc, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_id,
                            target_id,
                            relation,
                            float(weight),
                            _dt_to_iso(_utc_now()),
                            json.dumps(metadata or {}),
                        ),
                    )
                    self._backend_add_edge_locked(source_id, target_id, relation, float(weight))
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def neighbors(
        self,
        thought_id: str,
        *,
        hops: int = 1,
        relations: set[str] | None = None,
        limit: int = 100,
    ) -> list[str]:
        """Return reachable neighbor IDs up to N hops."""
        if hops <= 0:
            return []
        seen = {thought_id}
        out: list[str] = []
        queue = deque([(thought_id, 0)])
        while queue and len(out) < limit:
            node, depth = queue.popleft()
            if depth >= hops:
                continue
            remaining = max(1, limit - len(out))
            # Bound edge fan-out per node to keep traversal latency predictable.
            fetch_cap = max(remaining * 2, 8)
            with self._lock:
                rows = self._conn.execute(
                    "SELECT target_id, relation FROM thought_graph_edges WHERE source_id = ? LIMIT ?",
                    (node, fetch_cap),
                ).fetchall()
            for row in rows:
                nxt = str(row["target_id"])
                rel = str(row["relation"])
                if relations and rel not in relations:
                    continue
                if nxt in seen:
                    continue
                seen.add(nxt)
                out.append(nxt)
                queue.append((nxt, depth + 1))
        return out

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        *,
        max_depth: int = 4,
        limit: int = 10,
        relations: set[str] | None = None,
    ) -> list[list[str]]:
        """Find directed paths from source to target by bounded BFS."""
        if source_id == target_id:
            return [[source_id]]
        with self._lock:
            edges = self._conn.execute(
                "SELECT source_id, target_id, relation FROM thought_graph_edges"
            ).fetchall()
        adjacency: dict[str, list[tuple[str, str]]] = {}
        for row in edges:
            src = str(row["source_id"])
            tgt = str(row["target_id"])
            rel = str(row["relation"])
            adjacency.setdefault(src, []).append((tgt, rel))

        paths: list[list[str]] = []
        queue = deque([[source_id]])
        while queue and len(paths) < limit:
            path = queue.popleft()
            if len(path) - 1 >= max_depth:
                continue
            last = path[-1]
            for nxt, rel in adjacency.get(last, []):
                if relations and rel not in relations:
                    continue
                if nxt in path:
                    continue
                new_path = path + [nxt]
                if nxt == target_id:
                    paths.append(new_path)
                    if len(paths) >= limit:
                        break
                else:
                    queue.append(new_path)
        return paths

    def cluster_by_topic(self, *, min_cluster_size: int = 2) -> list[list[str]]:
        """Cluster thought IDs using semantic links; backend-aware with built-in fallback."""
        min_cluster_size = max(1, min_cluster_size)
        with self._lock:
            nodes = [
                str(row["thought_id"])
                for row in self._conn.execute("SELECT thought_id FROM thought_graph_nodes").fetchall()
            ]
            edges = self._conn.execute(
                "SELECT source_id, target_id, relation, weight FROM thought_graph_edges"
            ).fetchall()

        semantic_edges = [
            (str(row["source_id"]), str(row["target_id"]), float(row["weight"]))
            for row in edges
            if str(row["relation"]) == "semantic-similarity"
        ]

        if self._backend_name == "networkx" and semantic_edges:
            g = self._nx.Graph()
            g.add_nodes_from(nodes)
            g.add_weighted_edges_from(semantic_edges)
            communities = self._nx.algorithms.community.greedy_modularity_communities(g, weight="weight")
            return [sorted([str(node) for node in community]) for community in communities if len(community) >= min_cluster_size]

        if self._backend_name == "igraph" and semantic_edges:
            g = self._igraph.Graph(directed=False)
            g.add_vertices(nodes)
            index = {name: idx for idx, name in enumerate(nodes)}
            edge_idx = [(index[s], index[t]) for s, t, _ in semantic_edges if s in index and t in index]
            g.add_edges(edge_idx)
            clusters = g.connected_components(mode="weak")
            out: list[list[str]] = []
            for cluster in clusters:
                if len(cluster) >= min_cluster_size:
                    out.append(sorted([nodes[i] for i in cluster]))
            return out

        # Built-in fallback: connected components on undirected semantic adjacency.
        adjacency: dict[str, set[str]] = {n: set() for n in nodes}
        for src, tgt, _ in semantic_edges:
            adjacency.setdefault(src, set()).add(tgt)
            adjacency.setdefault(tgt, set()).add(src)

        visited: set[str] = set()
        clusters: list[list[str]] = []
        for node in nodes:
            if node in visited:
                continue
            queue = deque([node])
            component = []
            visited.add(node)
            while queue:
                cur = queue.popleft()
                component.append(cur)
                for nxt in adjacency.get(cur, set()):
                    if nxt in visited:
                        continue
                    visited.add(nxt)
                    queue.append(nxt)
            if len(component) >= min_cluster_size:
                clusters.append(sorted(component))
        return clusters

    def temporal_range(
        self,
        *,
        start_time_utc: datetime,
        end_time_utc: datetime,
        session_id: str | None = None,
        limit: int = 200,
    ) -> list[Thought]:
        """Return thoughts linked as graph nodes within a time range."""
        params: list[object] = [_dt_to_iso(start_time_utc), _dt_to_iso(end_time_utc)]
        where = ["n.timestamp_utc >= ?", "n.timestamp_utc <= ?"]
        if session_id is not None:
            where.append("n.session_id = ?")
            params.append(session_id)

        sql = f"""
            SELECT t.*
            FROM thought_graph_nodes n
            JOIN thoughts t ON t.id = n.thought_id
            WHERE {' AND '.join(where)}
            ORDER BY n.timestamp_utc ASC
            LIMIT ?
        """
        params.append(max(1, limit))
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._store._row_to_thought(row) for row in rows]

    async def aadd_thought(self, thought: Thought, **kwargs) -> Thought:
        return await asyncio.to_thread(self.add_thought, thought, **kwargs)

    async def alink(self, source_id: str, target_id: str, **kwargs) -> None:
        await asyncio.to_thread(self.link, source_id, target_id, **kwargs)

    async def afind_paths(self, source_id: str, target_id: str, **kwargs) -> list[list[str]]:
        return await asyncio.to_thread(self.find_paths, source_id, target_id, **kwargs)

    async def acluster_by_topic(self, **kwargs) -> list[list[str]]:
        return await asyncio.to_thread(self.cluster_by_topic, **kwargs)

    async def atemporal_range(self, **kwargs) -> list[Thought]:
        return await asyncio.to_thread(self.temporal_range, **kwargs)
