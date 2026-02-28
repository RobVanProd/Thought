import asyncio
import unittest

from thought_wrapper.sdk import ThoughtLLM, ThoughtLLMConfig
from thought_wrapper.tms import HashEmbedder, ReflectionEngine, Thought, ThoughtGraph, ThoughtStore


class _FakeClient:
    provider_name = "fake"

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if not self._outputs:
            return "Final response only."
        return self._outputs.pop(0)


class TestSdkThoughtLLM(unittest.TestCase):
    def setUp(self) -> None:
        self.embedder = HashEmbedder(dimension=32)
        self.store = ThoughtStore(embedding_dim=32, vector_backend="numpy")
        self.graph = ThoughtGraph(self.store)
        self.reflection = ReflectionEngine(
            self.store,
            graph=self.graph,
            embedder=self.embedder,
            embedding_dim=32,
        )

    def tearDown(self) -> None:
        self.store.close()

    def _make_llm(self, outputs: list[str], **config_kwargs) -> ThoughtLLM:
        client = _FakeClient(outputs)
        config = ThoughtLLMConfig(model="mock-model", **config_kwargs)
        return ThoughtLLM(
            client,
            store=self.store,
            graph=self.graph,
            reflection_engine=self.reflection,
            embedder=self.embedder,
            config=config,
        )

    def test_complete_xml_ingestion_and_cleaning(self) -> None:
        llm = self._make_llm(
            [
                '<thought id="th-1" category="reasoning" confidence="0.95">'
                "validate context"
                "</thought>\nFinal answer: accepted."
            ],
            thought_tagging_enforcement="xml",
            reflect_enabled=False,
        )
        out = llm.complete("Run validation", session_id="s_xml")
        self.assertEqual(len(out.stored_thoughts), 1)
        self.assertEqual(out.stored_thoughts[0].id, "th-1")
        self.assertNotIn("<thought", out.cleaned_output)
        self.assertIn("Final answer", out.cleaned_output)

    def test_complete_slash_enforcement_with_linear_fallback(self) -> None:
        llm = self._make_llm(
            ["Plan /thought[first [nested] step] done"],
            thought_tagging_enforcement="slash",
            reflect_enabled=False,
        )
        out = llm.complete("Build plan", session_id="s_slash", category="plan")
        self.assertEqual(len(out.stored_thoughts), 1)
        self.assertEqual(out.stored_thoughts[0].cleaned_text, "first [nested] step")
        self.assertNotIn("/thought[", out.cleaned_output)

    def test_reflection_frequency_behavior(self) -> None:
        llm = self._make_llm(
            [
                '<thought id="a" category="reasoning" confidence="0.9">first</thought>\nDone 1',
                '<thought id="b" category="reasoning" confidence="0.9">second</thought>\nDone 2',
            ],
            thought_tagging_enforcement="xml",
            reflect_enabled=True,
            reflection_frequency=2,
        )
        first = llm.complete("step1", session_id="s_reflect")
        second = llm.complete("step2", session_id="s_reflect")
        self.assertIsNone(first.reflection)
        self.assertIsNotNone(second.reflection)
        self.assertTrue(second.reflection.stored_reflections)

    def test_cross_session_recall_via_parent_lineage(self) -> None:
        seed = Thought(
            session_id="root",
            category="fact",
            confidence=0.92,
            tags=["seed"],
            raw_text="launch readiness checklist includes rollback plan",
            cleaned_text="launch readiness checklist includes rollback plan",
            embedding_vector=self.embedder.embed("launch readiness checklist includes rollback plan"),
            embedding_dim=32,
        )
        self.graph.add_thought(seed, semantic_neighbors=0)

        llm = self._make_llm(
            ['<thought id="c" category="reasoning" confidence="0.9">use parent memory</thought>\nAnswer'],
            thought_tagging_enforcement="xml",
            reflect_enabled=False,
        )
        out = llm.complete("launch readiness", session_id="child", parent_session_id="root")
        recalled_ids = {t.id for t in out.recalled_context}
        self.assertIn(seed.id, recalled_ids)

    def test_async_complete(self) -> None:
        llm = self._make_llm(
            ['<thought id="async-1" category="reasoning" confidence="0.9">async pass</thought>\nok'],
            thought_tagging_enforcement="xml",
            reflect_enabled=False,
        )

        async def _run() -> None:
            out = await llm.acomplete("async query", session_id="s_async")
            self.assertEqual(len(out.stored_thoughts), 1)
            self.assertEqual(out.stored_thoughts[0].id, "async-1")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
