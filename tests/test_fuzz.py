import random
import string
import unittest

from thought_wrapper import clean_thought_tags, parse_thought_tags


def _random_token(rng: random.Random, min_len: int = 0, max_len: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits + " .,;:-_/\n\t[]()"
    size = rng.randint(min_len, max_len)
    value = "".join(rng.choice(alphabet) for _ in range(size))
    # Keep regex test deterministic by excluding closing bracket from valid tag payload.
    return value.replace("]", "")


def _build_case(rng: random.Random) -> tuple[str, dict[str, str]]:
    segments = []
    expected = {}
    tag_count = rng.randint(0, 25)

    for i in range(tag_count):
        segments.append(_random_token(rng))
        content = _random_token(rng, min_len=1, max_len=120)
        segments.append(f"/thought[{content}]")
        expected[f"thought_{i}"] = content.strip()

    segments.append(_random_token(rng))
    return "".join(segments), expected


class TestFuzz(unittest.TestCase):
    def test_randomized_extraction_accuracy(self) -> None:
        rng = random.Random(20260228)
        total_cases = 400

        for _ in range(total_cases):
            text, expected = _build_case(rng)
            extracted = parse_thought_tags(text)
            self.assertEqual(extracted, expected)

    def test_clean_output_has_no_tag_markers(self) -> None:
        rng = random.Random(20260228)
        total_cases = 250

        for _ in range(total_cases):
            text, _ = _build_case(rng)
            cleaned = clean_thought_tags(text)
            self.assertNotIn("/thought[", cleaned)
            self.assertEqual(cleaned, clean_thought_tags(cleaned))


if __name__ == "__main__":
    unittest.main()

