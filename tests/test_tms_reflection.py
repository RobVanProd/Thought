import asyncio
import unittest

from thought_wrapper.tms import HashEmbedder, ReflectionEngine, Thought, ThoughtGraph, ThoughtStore
from thought_wrapper.tms.reflection import parse_structured_thoughts


class TestTmsReflection(unittest.TestCase):
    def setUp(self) -> None:
        self.embedder = HashEmbedder(dimension=16)
        self.store = ThoughtStore(embedding_dim=16, vector_backend="numpy")
        self.graph = ThoughtGraph(self.store)
        self.engine = ReflectionEngine(
            self.store,
            graph=self.graph,
            embedder=self.embedder,
            embedding_dim=16,
        )

    def tearDown(self) -> None:
        self.store.close()

    def _seed(self, session_id: str, text: str) -> Thought:
        t = Thought(
            session_id=session_id,
            category="reasoning",
            confidence=0.9,
            tags=["seed"],
            raw_text=text,
            cleaned_text=text,
            embedding_vector=self.embedder.embed(text),
            embedding_dim=16,
        )
        self.graph.add_thought(t, semantic_neighbors=0)
        return t

    def test_parse_structured_thoughts(self) -> None:
        text = (
            '<thought id="a" category="plan" confidence="0.95">step one</thought>'
            '<thought id="b" category="reflection" confidence="0.85">check risk</thought>'
        )
        parsed = parse_structured_thoughts(text)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].thought_id, "a")
        self.assertEqual(parsed[0].category, "plan")
        self.assertAlmostEqual(parsed[0].confidence, 0.95)

    def test_reflect_default_cycle(self) -> None:
        self.store.create_session("s1")
        self._seed("s1", "launch readiness requires checklist")
        out = self.engine.reflect(query="launch readiness", current_session_id="s1", mode="reasoning", top_k=5)
        self.assertGreaterEqual(len(out.stored_reflections), 1)
        persisted = self.store.retrieve(limit=100)
        categories = {t.category for t in persisted}
        self.assertIn("reflection", categories)

    def test_reflect_with_child_reflection_session(self) -> None:
        self.store.create_session("parent")
        self._seed("parent", "prior memory")
        out = self.engine.reflect(
            query="prior",
            current_session_id="parent",
            mode="summarization",
            top_k=3,
            reflection_session_id="parent_reflect",
        )
        self.assertTrue(out.stored_reflections)
        lineage = self.store.get_session_lineage("parent_reflect")
        self.assertEqual(lineage[:2], ["parent_reflect", "parent"])

    def test_reflect_with_custom_llm_callable(self) -> None:
        self.store.create_session("s2")
        self._seed("s2", "memory A")

        def fake_llm(prompt: str) -> str:
            self.assertIn("Return only <thought", prompt)
            return '<thought id="x1" category="reflection" confidence="0.9">custom reflection</thought>'

        out = self.engine.reflect(
            query="memory A",
            current_session_id="s2",
            mode="contradiction_detection",
            llm_callable=fake_llm,
        )
        self.assertEqual(len(out.stored_reflections), 1)
        self.assertEqual(out.stored_reflections[0].id, "x1")

    def test_async_reflect(self) -> None:
        async def _run() -> None:
            self.store.create_session("s3")
            self._seed("s3", "async memory")
            out = await self.engine.areflect(query="async", current_session_id="s3", mode="planning")
            self.assertGreaterEqual(len(out.stored_reflections), 1)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()

