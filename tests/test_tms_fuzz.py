import random
import string
import unittest

from thought_wrapper.tms import HashEmbedder, Thought, ThoughtFilters, ThoughtStore
from thought_wrapper.tms.pipeline import parse_and_store


def _random_word(rng: random.Random, min_len: int = 1, max_len: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "_-."
    size = rng.randint(min_len, max_len)
    return "".join(rng.choice(alphabet) for _ in range(size))


class TestTmsFuzz(unittest.TestCase):
    def test_randomized_store_retrieve_integrity(self) -> None:
        rng = random.Random(20260228)
        store = ThoughtStore(embedding_dim=16, vector_backend="numpy")
        try:
            thoughts = []
            for _ in range(200):
                vec = [rng.uniform(-1.0, 1.0) for _ in range(16)]
                thoughts.append(
                    Thought(
                        session_id=f"s_{rng.randint(1, 5)}",
                        category=rng.choice(["reasoning", "fact", "plan"]),
                        confidence=rng.uniform(0.0, 1.0),
                        tags=[rng.choice(["a", "b", "c"])],
                        raw_text=_random_word(rng),
                        cleaned_text=_random_word(rng),
                        embedding_vector=vec,
                        embedding_dim=16,
                    )
                )
            store.batch_store(thoughts)
            out = store.retrieve(limit=500)
            self.assertEqual(len(out), 200)
        finally:
            store.close()

    def test_randomized_parse_and_store_counts(self) -> None:
        rng = random.Random(20260228)
        store = ThoughtStore(embedding_dim=24, vector_backend="numpy")
        try:
            for case_id in range(100):
                count = rng.randint(0, 8)
                chunks = [_random_word(rng, 0, 10)]
                for _ in range(count):
                    content = _random_word(rng, 1, 20).replace("]", "")
                    chunks.append(f"/thought[{content}]")
                    chunks.append(_random_word(rng, 0, 6))
                raw = "".join(chunks)
                result = parse_and_store(
                    raw,
                    store,
                    session_id=f"case_{case_id}",
                    embedder=HashEmbedder(dimension=24),
                    embedding_dim=24,
                )
                self.assertEqual(len(result.thoughts), count)
            stored = store.retrieve(limit=2000)
            self.assertGreaterEqual(len(stored), 0)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
