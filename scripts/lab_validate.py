"""Runs full lab-grade validation: tests + benchmark + report generation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thought_wrapper import clean_thought_tags, parse_thought_tags
from thought_wrapper.samples import (
    EXPECTED_SPEC_CLEAN_OUTPUT,
    EXPECTED_SPEC_THOUGHTS,
    RAW_SPEC_OUTPUT,
)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, text=True, capture_output=True)


def _make_report(
    report_path: Path,
    unittest_result: subprocess.CompletedProcess[str],
    benchmark_path: Path,
    benchmark: dict,
    spec_dict_ok: bool,
    spec_clean_ok: bool,
) -> None:
    spec = benchmark["spec_sample"]
    accuracy = benchmark["accuracy"]
    lines = [
        "# Lab Validation Report",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "- Method: deterministic unit tests + reproducible timing benchmark + randomized accuracy study",
        "",
        "## Gate Status",
        "",
        f"- Unit tests: {'PASS' if unittest_result.returncode == 0 else 'FAIL'}",
        f"- Spec dictionary reproduction: {'PASS' if spec_dict_ok else 'FAIL'}",
        f"- Spec clean-output reproduction: {'PASS' if spec_clean_ok else 'FAIL'}",
        "",
        "## Spec Benchmark (Section 5 Input)",
        "",
        f"- Input size: {spec['input_chars']} chars",
        f"- Tag count: {spec['tag_count']}",
        f"- Regex parse avg: {spec['regex_parse']['avg_ms']:.6f} ms",
        f"- Regex clean avg: {spec['regex_clean']['avg_ms']:.6f} ms",
        f"- Regex total avg overhead: {spec['regex_parse']['avg_ms'] + spec['regex_clean']['avg_ms']:.6f} ms",
        f"- Linear parse avg: {spec['linear_parse']['avg_ms']:.6f} ms",
        f"- Linear clean avg: {spec['linear_clean']['avg_ms']:.6f} ms",
        "",
        "## Accuracy Study",
        "",
        f"- Cases: {accuracy['cases']}",
        f"- Total expected tags: {accuracy['total_expected_tags']}",
        f"- Exact-case accuracy: {accuracy['exact_case_accuracy_pct']:.2f}%",
        f"- Per-tag accuracy: {accuracy['per_tag_accuracy_pct']:.2f}%",
        "",
        "## Scaling Snapshot",
        "",
    ]

    for row in benchmark["scaling"]:
        lines.append(
            f"- {row['chars']} chars / {row['tags']} tags: "
            f"parse avg {row['parse']['avg_ms']:.6f} ms, clean avg {row['clean']['avg_ms']:.6f} ms"
        )

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Benchmark JSON: `{benchmark_path.as_posix()}`",
            "",
            "## Unit Test Output",
            "",
            "```text",
            unittest_result.stdout.strip() or "(no stdout)",
            unittest_result.stderr.strip() or "(no stderr)",
            "```",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lab-grade validator for thought wrapper.")
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--scale-runs", type=int, default=1000)
    parser.add_argument("--accuracy-cases", type=int, default=1000)
    parser.add_argument("--benchmark-output", type=Path, default=Path("results/benchmark_results.json"))
    parser.add_argument("--report-output", type=Path, default=Path("results/lab_validation_report.md"))
    args = parser.parse_args()

    unit = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    benchmark = _run(
        [
            sys.executable,
            "scripts/benchmark.py",
            "--runs",
            str(args.runs),
            "--scale-runs",
            str(args.scale_runs),
            "--accuracy-cases",
            str(args.accuracy_cases),
            "--output",
            str(args.benchmark_output),
        ]
    )

    if benchmark.returncode != 0:
        sys.stderr.write(benchmark.stdout + benchmark.stderr)
        return benchmark.returncode

    bench_data = json.loads(args.benchmark_output.read_text(encoding="utf-8"))
    spec_dict_ok = parse_thought_tags(RAW_SPEC_OUTPUT) == EXPECTED_SPEC_THOUGHTS
    spec_clean_ok = clean_thought_tags(RAW_SPEC_OUTPUT) == EXPECTED_SPEC_CLEAN_OUTPUT

    _make_report(
        report_path=args.report_output,
        unittest_result=unit,
        benchmark_path=args.benchmark_output,
        benchmark=bench_data,
        spec_dict_ok=spec_dict_ok,
        spec_clean_ok=spec_clean_ok,
    )

    sys.stdout.write(unit.stdout)
    if unit.stderr:
        sys.stderr.write(unit.stderr)
    sys.stdout.write(benchmark.stdout)
    if benchmark.stderr:
        sys.stderr.write(benchmark.stderr)
    sys.stdout.write(f"Report written to {args.report_output}\n")

    if unit.returncode != 0:
        return unit.returncode
    if not spec_dict_ok or not spec_clean_ok:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
