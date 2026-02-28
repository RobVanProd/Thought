"""Empirical benchmark harness for thought-tag parsing and cleaning."""

from __future__ import annotations

import argparse
import json
import math
import platform
import random
import statistics
import string
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thought_wrapper import (
    clean_thought_tags,
    clean_thought_tags_linear,
    parse_thought_tags,
    parse_thought_tags_linear,
)
from thought_wrapper.samples import RAW_SPEC_OUTPUT


def _stats(values: List[float]) -> Dict[str, float]:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return {"count": 0}
    p50_idx = int(0.50 * (count - 1))
    p95_idx = int(0.95 * (count - 1))
    return {
        "count": count,
        "avg_ms": sum(ordered) / count,
        "median_ms": ordered[p50_idx],
        "p95_ms": ordered[p95_idx],
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "std_ms": statistics.pstdev(ordered) if count > 1 else 0.0,
    }


def _time_function(fn: Callable[[], object], runs: int, warmup: int = 200) -> List[float]:
    for _ in range(warmup):
        fn()

    samples = []
    for _ in range(runs):
        start = perf_counter()
        fn()
        end = perf_counter()
        samples.append((end - start) * 1000.0)
    return samples


def _random_text(rng: random.Random, size: int) -> str:
    alphabet = string.ascii_letters + string.digits + " .,;:-_/\n\t"
    return "".join(rng.choice(alphabet) for _ in range(size))


def _make_synthetic_output(total_chars: int, tag_count: int, seed: int) -> str:
    rng = random.Random(seed)
    if tag_count <= 0:
        return _random_text(rng, total_chars)

    overhead_per_tag = len("/thought[]\n")
    budget_for_payload = max(0, total_chars - (tag_count * overhead_per_tag))
    content_per_tag = max(8, budget_for_payload // tag_count)

    chunks = ["Synthetic run start.\n"]
    for _ in range(tag_count):
        chunks.append(_random_text(rng, max(4, content_per_tag // 2)))
        content = _random_text(rng, content_per_tag).replace("]", "")
        chunks.append(f"\n/thought[{content}]\n")
    chunks.append("Synthetic run end.")
    return "".join(chunks)


def _accuracy_study(cases: int, max_tags: int = 30) -> Dict[str, float]:
    rng = random.Random(20260228)
    exact_case_matches = 0
    total_tags_expected = 0
    total_tags_matched = 0

    for _ in range(cases):
        tag_count = rng.randint(0, max_tags)
        text_chunks = []
        expected = {}
        for i in range(tag_count):
            text_chunks.append(_random_text(rng, rng.randint(0, 20)))
            content = _random_text(rng, rng.randint(1, 100)).replace("]", "")
            text_chunks.append(f"/thought[{content}]")
            expected[f"thought_{i}"] = content.strip()
        text_chunks.append(_random_text(rng, rng.randint(0, 20)))
        text = "".join(text_chunks)

        extracted = parse_thought_tags(text)
        if extracted == expected:
            exact_case_matches += 1

        total_tags_expected += len(expected)
        for key, expected_value in expected.items():
            if extracted.get(key) == expected_value:
                total_tags_matched += 1

    case_accuracy = (exact_case_matches / cases) * 100.0 if cases else math.nan
    tag_accuracy = (total_tags_matched / total_tags_expected) * 100.0 if total_tags_expected else 100.0
    return {
        "cases": cases,
        "total_expected_tags": total_tags_expected,
        "exact_case_accuracy_pct": case_accuracy,
        "per_tag_accuracy_pct": tag_accuracy,
    }


def run_benchmark(runs: int, scale_runs: int, accuracy_cases: int) -> Dict[str, object]:
    spec_parse_samples = _time_function(lambda: parse_thought_tags(RAW_SPEC_OUTPUT), runs=runs)
    spec_clean_samples = _time_function(lambda: clean_thought_tags(RAW_SPEC_OUTPUT), runs=runs)
    spec_parse_linear_samples = _time_function(lambda: parse_thought_tags_linear(RAW_SPEC_OUTPUT), runs=runs)
    spec_clean_linear_samples = _time_function(lambda: clean_thought_tags_linear(RAW_SPEC_OUTPUT), runs=runs)

    scale_matrix = [
        {"chars": 693, "tags": 4, "seed": 7},
        {"chars": 10_000, "tags": 50, "seed": 11},
        {"chars": 20_000, "tags": 100, "seed": 19},
    ]
    scaling_results = []
    for row in scale_matrix:
        text = _make_synthetic_output(total_chars=row["chars"], tag_count=row["tags"], seed=row["seed"])
        parse_samples = _time_function(lambda t=text: parse_thought_tags(t), runs=scale_runs, warmup=100)
        clean_samples = _time_function(lambda t=text: clean_thought_tags(t), runs=scale_runs, warmup=100)
        scaling_results.append(
            {
                "chars": row["chars"],
                "tags": row["tags"],
                "parse": _stats(parse_samples),
                "clean": _stats(clean_samples),
            }
        )

    benchmark_results = {
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "runs": runs,
            "scale_runs": scale_runs,
            "accuracy_cases": accuracy_cases,
        },
        "spec_sample": {
            "input_chars": len(RAW_SPEC_OUTPUT),
            "tag_count": len(parse_thought_tags(RAW_SPEC_OUTPUT)),
            "regex_parse": _stats(spec_parse_samples),
            "regex_clean": _stats(spec_clean_samples),
            "linear_parse": _stats(spec_parse_linear_samples),
            "linear_clean": _stats(spec_clean_linear_samples),
        },
        "scaling": scaling_results,
        "accuracy": _accuracy_study(cases=accuracy_cases),
    }
    return benchmark_results


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark /thought tag parsing and cleaning.")
    parser.add_argument("--runs", type=int, default=1000, help="Runs for the Section 5 reproduction benchmark.")
    parser.add_argument("--scale-runs", type=int, default=1000, help="Runs per scaling matrix entry.")
    parser.add_argument("--accuracy-cases", type=int, default=1000, help="Synthetic cases for accuracy study.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/benchmark_results.json"),
        help="Path to JSON output file.",
    )
    args = parser.parse_args()

    results = run_benchmark(runs=args.runs, scale_runs=args.scale_runs, accuracy_cases=args.accuracy_cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")

    spec = results["spec_sample"]
    accuracy = results["accuracy"]

    print("Benchmark complete.")
    print(f"Output: {args.output}")
    print(f"Spec sample chars: {spec['input_chars']}, tags: {spec['tag_count']}")
    print(f"Regex parse avg (ms): {spec['regex_parse']['avg_ms']:.6f}")
    print(f"Regex clean avg (ms): {spec['regex_clean']['avg_ms']:.6f}")
    print(f"Linear parse avg (ms): {spec['linear_parse']['avg_ms']:.6f}")
    print(f"Linear clean avg (ms): {spec['linear_clean']['avg_ms']:.6f}")
    print(f"Exact-case accuracy (%): {accuracy['exact_case_accuracy_pct']:.2f}")
    print(f"Per-tag accuracy (%): {accuracy['per_tag_accuracy_pct']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
