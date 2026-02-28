import random
import string
import unittest

from thought_wrapper.sdk import ThoughtLLM, ThoughtLLMConfig
from thought_wrapper.tms import HashEmbedder, ReflectionEngine, ThoughtGraph, ThoughtStore


class _FuzzClient:
    provider_name = "fuzz-client"

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.idx = 0

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        del system_prompt, user_prompt, model, temperature, max_tokens
        out = self.outputs[self.idx]
        self.idx += 1
        return out


def _rand_text(rng: random.Random, min_len: int = 5, max_len: int = 32) -> str:
    alphabet = string.ascii_lowercase + string.digits + " "
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(min_len, max_len))).strip() or "x"


class TestPhase4Fuzz(unittest.TestCase):
    def test_randomized_thought_ingestion(self) -> None:
        rng = random.Random(20260228)
        outputs_xml: list[str] = []
        outputs_slash: list[str] = []
        expected_xml_counts: list[int] = []
        expected_slash_counts: list[int] = []

        for i in range(120):
            thought_count = rng.randint(1, 4)
            expected_xml_counts.append(thought_count)
            expected_slash_counts.append(thought_count)

            xml_chunks = []
            slash_chunks = []
            for j in range(thought_count):
                content = _rand_text(rng).replace("<", "").replace(">", "")
                xml_chunks.append(
                    f'<thought id="fx-{i}-{j}" category="reasoning" confidence="0.9">{content}</thought>'
                )
                # Insert nested brackets often to exercise linear fallback compatibility.
                nested = f"{content} [n{j}]"
                slash_chunks.append(f"/thought[{nested}]")
            outputs_xml.append("\n".join(xml_chunks) + "\nFinal response.")
            outputs_slash.append("Intro " + " ".join(slash_chunks) + " End.")

        # XML enforcement fuzz.
        store_xml = ThoughtStore(embedding_dim=20, vector_backend="numpy")
        graph_xml = ThoughtGraph(store_xml)
        embedder_xml = HashEmbedder(dimension=20)
        reflection_xml = ReflectionEngine(store_xml, graph=graph_xml, embedder=embedder_xml, embedding_dim=20)
        llm_xml = ThoughtLLM(
            _FuzzClient(outputs_xml),
            store=store_xml,
            graph=graph_xml,
            reflection_engine=reflection_xml,
            embedder=embedder_xml,
            config=ThoughtLLMConfig(model="fuzz-xml", thought_tagging_enforcement="xml", reflect_enabled=False),
        )
        try:
            for i, expected in enumerate(expected_xml_counts):
                out = llm_xml.complete(f"xml-case-{i}", session_id="s_xml_fuzz")
                self.assertEqual(len(out.stored_thoughts), expected)
                self.assertNotIn("<thought", out.cleaned_output)
        finally:
            store_xml.close()

        # Slash enforcement fuzz.
        store_slash = ThoughtStore(embedding_dim=20, vector_backend="numpy")
        graph_slash = ThoughtGraph(store_slash)
        embedder_slash = HashEmbedder(dimension=20)
        reflection_slash = ReflectionEngine(
            store_slash,
            graph=graph_slash,
            embedder=embedder_slash,
            embedding_dim=20,
        )
        llm_slash = ThoughtLLM(
            _FuzzClient(outputs_slash),
            store=store_slash,
            graph=graph_slash,
            reflection_engine=reflection_slash,
            embedder=embedder_slash,
            config=ThoughtLLMConfig(model="fuzz-slash", thought_tagging_enforcement="slash", reflect_enabled=False),
        )
        try:
            for i, expected in enumerate(expected_slash_counts):
                out = llm_slash.complete(f"slash-case-{i}", session_id="s_slash_fuzz")
                self.assertEqual(len(out.stored_thoughts), expected)
                self.assertNotIn("/thought[", out.cleaned_output)
        finally:
            store_slash.close()


if __name__ == "__main__":
    unittest.main()
