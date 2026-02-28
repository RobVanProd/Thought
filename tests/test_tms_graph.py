import asyncio
import unittest
from datetime import datetime, timedelta, timezone

from thought_wrapper.tms import HashEmbedder, Thought, ThoughtFilters, ThoughtGraph, ThoughtStore


class TestTmsGraph(unittest.TestCase):
    def setUp(self) -> None:
        self.embedder = HashEmbedder(dimension=16)
        self.store = ThoughtStore(embedding_dim=16, vector_backend="numpy")
        self.graph = ThoughtGraph(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def _thought(self, text: str, *, session_id: str, ts: datetime | None = None) -> Thought:
        vec = self.embedder.embed(text)
        return Thought(
            session_id=session_id,
            category="reasoning",
            confidence=0.9,
            tags=[],
            raw_text=text,
            cleaned_text=text,
            embedding_vector=vec,
            embedding_dim=16,
            timestamp_utc=ts or datetime.now(timezone.utc),
        )

    def test_add_and_temporal_link(self) -> None:
        t1 = self._thought("first", session_id="s1", ts=datetime.now(timezone.utc) - timedelta(minutes=1))
        t2 = self._thought("second", session_id="s1", ts=datetime.now(timezone.utc))
        self.graph.add_thought(t1)
        self.graph.add_thought(t2)
        paths = self.graph.find_paths(t1.id, t2.id, max_depth=2, relations={"temporal-successor"})
        self.assertTrue(paths)

    def test_link_and_find_paths(self) -> None:
        a = self._thought("a", session_id="s")
        b = self._thought("b", session_id="s")
        c = self._thought("c", session_id="s")
        for t in (a, b, c):
            self.graph.add_thought(t)
        self.graph.link(a.id, b.id, relation="explicit-reference")
        self.graph.link(b.id, c.id, relation="explicit-reference")
        paths = self.graph.find_paths(a.id, c.id, max_depth=3)
        self.assertEqual(paths[0], [a.id, b.id, c.id])

    def test_cluster_by_topic(self) -> None:
        t1 = self._thought("cluster-a1", session_id="s")
        t2 = self._thought("cluster-a2", session_id="s")
        t3 = self._thought("cluster-b1", session_id="s")
        for t in (t1, t2, t3):
            self.graph.add_thought(t, semantic_neighbors=0)
        self.graph.link(t1.id, t2.id, relation="semantic-similarity", weight=0.95, bidirectional=True)
        clusters = self.graph.cluster_by_topic(min_cluster_size=2)
        flattened = [set(c) for c in clusters]
        self.assertIn({t1.id, t2.id}, flattened)

    def test_temporal_range(self) -> None:
        now = datetime.now(timezone.utc)
        old = self._thought("old", session_id="s", ts=now - timedelta(hours=2))
        mid = self._thought("mid", session_id="s", ts=now - timedelta(hours=1))
        new = self._thought("new", session_id="s", ts=now)
        for t in (old, mid, new):
            self.graph.add_thought(t, semantic_neighbors=0)
        out = self.graph.temporal_range(
            start_time_utc=now - timedelta(hours=1, minutes=30),
            end_time_utc=now + timedelta(minutes=1),
            session_id="s",
        )
        ids = {t.id for t in out}
        self.assertIn(mid.id, ids)
        self.assertIn(new.id, ids)
        self.assertNotIn(old.id, ids)

    def test_cross_session_recall_with_graph_expansion(self) -> None:
        self.store.create_session("root")
        self.store.create_session("child", parent_session_id="root")

        parent_t = self._thought("parent memory about launch readiness", session_id="root")
        child_t = self._thought("child topic reference", session_id="child")
        related_t = self._thought("linked parent memory detail", session_id="root")
        for t in (parent_t, child_t, related_t):
            self.graph.add_thought(t, semantic_neighbors=0)
        self.graph.link(parent_t.id, related_t.id, relation="explicit-reference")

        query_vec = self.embedder.embed("launch readiness")
        recalled = self.store.recall_from_prior_sessions(
            query_vec,
            current_session_id="child",
            graph=self.graph,
            limit=5,
            graph_hops=1,
        )
        recalled_ids = {s.thought.id for s in recalled}
        self.assertIn(parent_t.id, recalled_ids)
        self.assertIn(related_t.id, recalled_ids)
        self.assertNotIn(child_t.id, recalled_ids)

    def test_async_graph_methods(self) -> None:
        async def _run() -> None:
            a = self._thought("async-a", session_id="a")
            b = self._thought("async-b", session_id="a")
            await self.graph.aadd_thought(a)
            await self.graph.aadd_thought(b)
            await self.graph.alink(a.id, b.id, relation="explicit-reference")
            paths = await self.graph.afind_paths(a.id, b.id)
            self.assertTrue(paths)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()

