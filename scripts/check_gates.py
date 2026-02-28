"""CI gate checker for Python benchmark results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate benchmark gates.")
    parser.add_argument("--input", type=Path, required=True, help="Path to benchmark JSON")
    parser.add_argument("--min-accuracy", type=float, default=99.9)
    parser.add_argument("--max-p95-ms", type=float, default=1.0)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    accuracy = data["accuracy"]
    spec = data["spec_sample"]

    failures: list[str] = []
    if float(accuracy["exact_case_accuracy_pct"]) < args.min_accuracy:
        failures.append(
            f"exact-case accuracy {accuracy['exact_case_accuracy_pct']:.6f}% < {args.min_accuracy:.3f}%"
        )
    if float(accuracy["per_tag_accuracy_pct"]) < args.min_accuracy:
        failures.append(f"per-tag accuracy {accuracy['per_tag_accuracy_pct']:.6f}% < {args.min_accuracy:.3f}%")
    if float(spec["regex_parse"]["p95_ms"]) >= args.max_p95_ms:
        failures.append(f"regex parse p95 {spec['regex_parse']['p95_ms']:.6f} ms >= {args.max_p95_ms:.6f} ms")
    if float(spec["regex_clean"]["p95_ms"]) >= args.max_p95_ms:
        failures.append(f"regex clean p95 {spec['regex_clean']['p95_ms']:.6f} ms >= {args.max_p95_ms:.6f} ms")

    if failures:
        print("CI gates: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("CI gates: PASS")
    print(f"- exact-case accuracy: {accuracy['exact_case_accuracy_pct']:.6f}%")
    print(f"- per-tag accuracy: {accuracy['per_tag_accuracy_pct']:.6f}%")
    print(f"- regex parse p95: {spec['regex_parse']['p95_ms']:.6f} ms")
    print(f"- regex clean p95: {spec['regex_clean']['p95_ms']:.6f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

