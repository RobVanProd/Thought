import random
import unittest

from thought_wrapper.tms import HashEmbedder, ReflectionEngine, Thought, ThoughtGraph, ThoughtStore


class TestTmsGraphFuzz(unittest.TestCase):
    def test_random_graph_operations_stability(self) -> None:
        rng = random.Random(20260228)
        embedder = HashEmbedder(dimension=12)
        store = ThoughtStore(embedding_dim=12, vector_backend="numpy")
        graph = ThoughtGraph(store)
        try:
            thoughts: list[Thought] = []
            for i in range(120):
                content = f"node-{i}-{rng.randint(0, 9999)}"
                t = Thought(
                    session_id=f"s_{i % 6}",
                    category=rng.choice(["reasoning", "plan", "fact"]),
                    confidence=rng.random(),
                    tags=[rng.choice(["x", "y", "z"])],
                    raw_text=content,
                    cleaned_text=content,
                    embedding_vector=embedder.embed(content),
                    embedding_dim=12,
                )
                graph.add_thought(t, semantic_neighbors=0, temporal_link=False)
                thoughts.append(t)

            for _ in range(300):
                a = rng.choice(thoughts)
                b = rng.choice(thoughts)
                if a.id == b.id:
                    continue
                graph.link(
                    a.id,
                    b.id,
                    relation=rng.choice(["explicit-reference", "semantic-similarity", "temporal-successor"]),
                    weight=rng.uniform(0.1, 1.0),
                )

            for _ in range(30):
                src = rng.choice(thoughts).id
                tgt = rng.choice(thoughts).id
                graph.find_paths(src, tgt, max_depth=4, limit=5)
                graph.neighbors(src, hops=2, limit=20)

            graph.cluster_by_topic(min_cluster_size=2)
        finally:
            store.close()

    def test_random_reflection_cycles_stability(self) -> None:
        rng = random.Random(20260228)
        embedder = HashEmbedder(dimension=12)
        store = ThoughtStore(embedding_dim=12, vector_backend="numpy")
        graph = ThoughtGraph(store)
        engine = ReflectionEngine(store, graph=graph, embedder=embedder, embedding_dim=12)
        try:
            store.create_session("root")
            for i in range(40):
                text = f"memory-{i}-{rng.randint(0, 9999)}"
                graph.add_thought(
                    Thought(
                        session_id="root",
                        category="reasoning",
                        confidence=0.8,
                        tags=[],
                        raw_text=text,
                        cleaned_text=text,
                        embedding_vector=embedder.embed(text),
                        embedding_dim=12,
                    ),
                    semantic_neighbors=0,
                )

            modes = ["reasoning", "summarization", "contradiction_detection", "planning"]
            for i in range(30):
                mode = modes[i % len(modes)]
                result = engine.reflect(
                    query=f"query-{i}",
                    current_session_id="root",
                    mode=mode,
                    top_k=6,
                )
                self.assertGreaterEqual(len(result.stored_reflections), 1)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()

