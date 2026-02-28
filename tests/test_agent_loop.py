import asyncio
import unittest

from thought_wrapper.agent import AgentLoop
from thought_wrapper.sdk import ThoughtLLM, ThoughtLLMConfig
from thought_wrapper.tms import HashEmbedder, ReflectionEngine, ThoughtGraph, ThoughtStore


class _LoopClient:
    provider_name = "mock-loop"

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        del system_prompt, model, temperature, max_tokens
        snippet = user_prompt[:50].replace('"', "'")
        return (
            f'<thought id="loop-{abs(hash(snippet)) % 100000}" category="reasoning" confidence="0.91">'
            f"{snippet}"
            "</thought>\n"
            "Final answer."
        )


class TestAgentLoop(unittest.TestCase):
    def setUp(self) -> None:
        self.store = ThoughtStore(embedding_dim=24, vector_backend="numpy")
        self.graph = ThoughtGraph(self.store)
        self.embedder = HashEmbedder(dimension=24)
        self.reflection = ReflectionEngine(
            self.store,
            graph=self.graph,
            embedder=self.embedder,
            embedding_dim=24,
        )
        self.llm = ThoughtLLM(
            _LoopClient(),
            store=self.store,
            graph=self.graph,
            reflection_engine=self.reflection,
            embedder=self.embedder,
            config=ThoughtLLMConfig(
                model="mock-loop",
                thought_tagging_enforcement="xml",
                reflect_enabled=True,
                reflection_frequency=1,
            ),
        )

    def tearDown(self) -> None:
        self.store.close()

    def test_run_turn_reflection_frequency(self) -> None:
        loop = AgentLoop(self.llm, reflection_frequency=2)
        t1 = loop.run_turn("first input", session_id="loop-s")
        t2 = loop.run_turn("second input", session_id="loop-s")
        self.assertEqual(t1.turn_index, 1)
        self.assertEqual(t2.turn_index, 2)
        self.assertIsNone(t1.completion.reflection)
        self.assertIsNotNone(t2.completion.reflection)

    def test_run_session(self) -> None:
        loop = AgentLoop(self.llm, reflection_frequency=1)
        out = loop.run_session(["one", "two", "three"], session_id="loop-session")
        self.assertEqual(len(out.turns), 3)
        self.assertEqual(out.turns[0].turn_index, 1)
        self.assertTrue(all(turn.completion.stored_thoughts for turn in out.turns))

    def test_async_run(self) -> None:
        loop = AgentLoop(self.llm, reflection_frequency=1)

        async def _run() -> None:
            turn = await loop.arun_turn("async input", session_id="loop-async")
            self.assertEqual(turn.turn_index, 1)
            session = await loop.arun_session(["a", "b"], session_id="loop-async-2")
            self.assertEqual(len(session.turns), 2)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
