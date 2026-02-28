import asyncio
import unittest
from datetime import datetime, timedelta, timezone

from thought_wrapper.tms import HashEmbedder, Thought, ThoughtFilters, ThoughtStore
from thought_wrapper.tms.pipeline import parse_and_store


class TestTmsCore(unittest.TestCase):
    def test_thought_model_validates_confidence(self) -> None:
        with self.assertRaises(Exception):
            Thought(
                session_id="s1",
                category="reasoning",
                confidence=1.5,
                tags=[],
                raw_text="x",
                cleaned_text="x",
                embedding_vector=[0.1, 0.2],
                embedding_dim=2,
            )

    def test_store_and_retrieve_roundtrip(self) -> None:
        store = ThoughtStore(embedding_dim=4, vector_backend="numpy")
        try:
            thought = Thought(
                session_id="session_a",
                category="reasoning",
                confidence=0.8,
                tags=["alpha"],
                raw_text="raw",
                cleaned_text="clean",
                embedding_vector=[1.0, 0.0, 0.0, 0.0],
                embedding_dim=4,
            )
            store.store(thought)
            out = store.retrieve(limit=10)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0].id, thought.id)
            self.assertEqual(out[0].session_id, "session_a")
        finally:
            store.close()

    def test_batch_store_is_atomic_on_error(self) -> None:
        store = ThoughtStore(embedding_dim=4, vector_backend="numpy")
        try:
            good = Thought(
                session_id="s",
                category="reasoning",
                confidence=0.8,
                tags=[],
                raw_text="a",
                cleaned_text="a",
                embedding_vector=[1.0, 0.0, 0.0, 0.0],
                embedding_dim=4,
            )
            bad = Thought(
                session_id="s",
                category="reasoning",
                confidence=0.8,
                tags=[],
                raw_text="b",
                cleaned_text="b",
                embedding_vector=[1.0, 0.0, 0.0],
                embedding_dim=3,
            )
            with self.assertRaises(ValueError):
                store.batch_store([good, bad])
            self.assertEqual(store.retrieve(limit=10), [])
        finally:
            store.close()

    def test_retrieve_with_filters(self) -> None:
        store = ThoughtStore(embedding_dim=4, vector_backend="numpy")
        try:
            now = datetime.now(timezone.utc)
            thoughts = [
                Thought(
                    session_id="s1",
                    category="reasoning",
                    confidence=0.9,
                    tags=["plan"],
                    raw_text="a",
                    cleaned_text="a",
                    embedding_vector=[1, 0, 0, 0],
                    embedding_dim=4,
                    timestamp_utc=now - timedelta(minutes=5),
                ),
                Thought(
                    session_id="s2",
                    category="fact",
                    confidence=0.4,
                    tags=["fact"],
                    raw_text="b",
                    cleaned_text="b",
                    embedding_vector=[0, 1, 0, 0],
                    embedding_dim=4,
                    timestamp_utc=now,
                ),
            ]
            store.batch_store(thoughts)
            out = store.retrieve(
                filters=ThoughtFilters(session_id="s1", min_confidence=0.7, tags_any=["plan"]),
                limit=10,
            )
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0].session_id, "s1")
        finally:
            store.close()

    def test_semantic_search_ranking(self) -> None:
        store = ThoughtStore(embedding_dim=4, vector_backend="numpy")
        try:
            thoughts = [
                Thought(
                    session_id="s1",
                    category="reasoning",
                    confidence=0.9,
                    tags=[],
                    raw_text="alpha",
                    cleaned_text="alpha",
                    embedding_vector=[1, 0, 0, 0],
                    embedding_dim=4,
                ),
                Thought(
                    session_id="s1",
                    category="reasoning",
                    confidence=0.9,
                    tags=[],
                    raw_text="beta",
                    cleaned_text="beta",
                    embedding_vector=[0, 1, 0, 0],
                    embedding_dim=4,
                ),
            ]
            store.batch_store(thoughts)
            results = store.semantic_search([1, 0, 0, 0], limit=2)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].thought.raw_text, "alpha")
            self.assertGreaterEqual(results[0].semantic_score, results[1].semantic_score)
        finally:
            store.close()

    def test_async_methods(self) -> None:
        async def _run() -> None:
            store = ThoughtStore(embedding_dim=4, vector_backend="numpy")
            try:
                thought = Thought(
                    session_id="s1",
                    category="reasoning",
                    confidence=0.9,
                    tags=[],
                    raw_text="async",
                    cleaned_text="async",
                    embedding_vector=[1, 0, 0, 0],
                    embedding_dim=4,
                )
                await store.astore(thought)
                out = await store.aretrieve(limit=10)
                self.assertEqual(len(out), 1)
                search = await store.asemantic_search([1, 0, 0, 0], limit=1)
                self.assertEqual(len(search), 1)
            finally:
                store.close()

        asyncio.run(_run())

    def test_parse_and_store_pipeline_regex(self) -> None:
        store = ThoughtStore(embedding_dim=8, vector_backend="numpy")
        try:
            raw = "Intro /thought[first] middle /thought[second] outro"
            result = parse_and_store(
                raw,
                store,
                session_id="session_pipeline",
                confidence=0.7,
                tags=["pipeline"],
                embedder=HashEmbedder(dimension=8),
                embedding_dim=8,
            )
            self.assertFalse(result.used_linear_fallback)
            self.assertEqual(len(result.thoughts), 2)
            persisted = store.retrieve(filters=ThoughtFilters(session_id="session_pipeline"), limit=10)
            self.assertEqual(len(persisted), 2)
        finally:
            store.close()

    def test_parse_and_store_pipeline_linear_fallback(self) -> None:
        store = ThoughtStore(embedding_dim=8, vector_backend="numpy")
        try:
            raw = "A /thought[x [nested] y] B"
            result = parse_and_store(
                raw,
                store,
                session_id="session_nested",
                embedder=HashEmbedder(dimension=8),
                embedding_dim=8,
            )
            self.assertTrue(result.used_linear_fallback)
            self.assertEqual(result.thoughts[0].cleaned_text, "x [nested] y")
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()

