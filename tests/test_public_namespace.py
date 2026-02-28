import unittest


class TestPublicNamespace(unittest.TestCase):
    def test_thoughtwrapper_core_alias(self) -> None:
        from thoughtwrapper import clean_thought_tags, parse_thought_tags

        text = "A /thought[first] B"
        self.assertEqual(parse_thought_tags(text), {"thought_0": "first"})
        self.assertEqual(clean_thought_tags(text), "A\nB")

    def test_thoughtwrapper_tms_alias(self) -> None:
        from thoughtwrapper.tms import HashEmbedder, ThoughtStore

        store = ThoughtStore(embedding_dim=8, vector_backend="numpy")
        try:
            embedder = HashEmbedder(dimension=8)
            vec = embedder.embed("alias-test")
            self.assertEqual(len(vec), 8)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
