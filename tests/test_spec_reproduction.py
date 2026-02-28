import time
import unittest

from thought_wrapper import clean_thought_tags, parse_thought_tags
from thought_wrapper.samples import (
    EXPECTED_SPEC_CLEAN_OUTPUT,
    EXPECTED_SPEC_THOUGHTS,
    RAW_SPEC_OUTPUT,
)


class TestSpecReproduction(unittest.TestCase):
    def test_exact_hash_map_reproduction(self) -> None:
        thoughts = parse_thought_tags(RAW_SPEC_OUTPUT)
        self.assertEqual(thoughts, EXPECTED_SPEC_THOUGHTS)

    def test_exact_clean_output_reproduction(self) -> None:
        cleaned = clean_thought_tags(RAW_SPEC_OUTPUT)
        self.assertEqual(cleaned, EXPECTED_SPEC_CLEAN_OUTPUT)

    def test_latency_is_sub_millisecond_class(self) -> None:
        runs = 1000
        parse_times_ms = []
        clean_times_ms = []

        for _ in range(runs):
            parse_start = time.perf_counter()
            parse_thought_tags(RAW_SPEC_OUTPUT)
            parse_end = time.perf_counter()

            clean_start = time.perf_counter()
            clean_thought_tags(RAW_SPEC_OUTPUT)
            clean_end = time.perf_counter()

            parse_times_ms.append((parse_end - parse_start) * 1000.0)
            clean_times_ms.append((clean_end - clean_start) * 1000.0)

        avg_parse_ms = sum(parse_times_ms) / runs
        avg_clean_ms = sum(clean_times_ms) / runs

        self.assertLess(avg_parse_ms, 1.0)
        self.assertLess(avg_clean_ms, 1.0)


if __name__ == "__main__":
    unittest.main()

