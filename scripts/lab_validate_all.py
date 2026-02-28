"""Consolidated lab validator for Python/TypeScript/Java wrappers + full TMS stack."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: float) -> str:
    return f"{value:.6f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidated validation runner")
    parser.add_argument("--python-runs", type=int, default=1000)
    parser.add_argument("--tms-runs", type=int, default=500)
    parser.add_argument("--tms-corpus", type=int, default=1500)
    parser.add_argument("--graph-runs", type=int, default=300)
    parser.add_argument("--graph-corpus", type=int, default=900)
    parser.add_argument("--agent-runs", type=int, default=180)
    parser.add_argument("--agent-reflection-frequency", type=int, default=2)
    parser.add_argument("--agent-seed-count", type=int, default=40)
    parser.add_argument("--report-output", type=Path, default=Path("results/lab_validation_report.md"))
    args = parser.parse_args()

    py_tests = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    py_bench = _run(
        [
            sys.executable,
            "scripts/benchmark.py",
            "--runs",
            str(args.python_runs),
            "--scale-runs",
            str(args.python_runs),
            "--accuracy-cases",
            "1000",
            "--output",
            "results/benchmark_results.json",
        ]
    )
    tms_bench = _run(
        [
            sys.executable,
            "scripts/tms_benchmark.py",
            "--runs",
            str(args.tms_runs),
            "--corpus-size",
            str(args.tms_corpus),
            "--output",
            "results/tms_benchmark_results.json",
        ]
    )
    graph_bench = _run(
        [
            sys.executable,
            "scripts/tms_graph_benchmark.py",
            "--runs",
            str(args.graph_runs),
            "--corpus-size",
            str(args.graph_corpus),
            "--output",
            "results/tms_graph_benchmark_results.json",
        ]
    )
    agent_bench = _run(
        [
            sys.executable,
            "scripts/agent_loop_benchmark.py",
            "--runs",
            str(args.agent_runs),
            "--reflection-frequency",
            str(args.agent_reflection_frequency),
            "--seed-count",
            str(args.agent_seed_count),
            "--output",
            "results/agent_loop_benchmark_results.json",
        ]
    )

    if py_bench.returncode != 0:
        sys.stderr.write(py_bench.stdout + py_bench.stderr)
        return py_bench.returncode
    if tms_bench.returncode != 0:
        sys.stderr.write(tms_bench.stdout + tms_bench.stderr)
        return tms_bench.returncode
    if graph_bench.returncode != 0:
        sys.stderr.write(graph_bench.stdout + graph_bench.stderr)
        return graph_bench.returncode
    if agent_bench.returncode != 0:
        sys.stderr.write(agent_bench.stdout + agent_bench.stderr)
        return agent_bench.returncode

    py_json = _load_json(Path("results/benchmark_results.json"))
    tms_json = _load_json(Path("results/tms_benchmark_results.json"))
    graph_json = _load_json(Path("results/tms_graph_benchmark_results.json"))
    agent_json = _load_json(Path("results/agent_loop_benchmark_results.json"))

    ts_path = Path("typescript/results/benchmark_results.json")
    java_path = Path("java/results/benchmark_results.json")
    ts_json = _load_json(ts_path) if ts_path.exists() else None
    java_json = _load_json(java_path) if java_path.exists() else None

    py_acc = py_json["accuracy"]
    py_spec = py_json["spec_sample"]
    py_pass = (
        py_tests.returncode == 0
        and py_acc["exact_case_accuracy_pct"] >= 99.9
        and py_acc["per_tag_accuracy_pct"] >= 99.9
        and py_spec["regex_parse"]["p95_ms"] < 1.0
        and py_spec["regex_clean"]["p95_ms"] < 1.0
    )
    tms_pass = tms_json["quality"]["top1_exact_match_pct"] >= 99.0
    reflection_pass = (
        graph_json["reflection_cycle"]["success_rate_pct"] >= 99.0
        and graph_json["reflection_cycle"]["latency"]["p95_ms"] < 50.0
    )
    agent = agent_json["agentic_loop"]
    phase4_pass = (
        agent["thought_store_success_rate_pct"] >= 99.0
        and agent["reflection_success_rate_pct"] >= 99.0
        and agent["recall_probe_hit_rate_pct"] >= 99.0
        and agent["turn_total_latency"]["p95_ms"] < 120.0
    )

    lines = [
        "# Consolidated Lab Validation Report",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        "- Scope: Python parser/cleaner, TypeScript port, Java port, Python TMS core, ThoughtGraph, Reflection Engine, and Phase 4 multi-model/agentic loop integrations",
        "",
        "## Gate Status",
        "",
        f"- Python tests: {'PASS' if py_tests.returncode == 0 else 'FAIL'}",
        f"- Python parser gates (accuracy>=99.9, p95<1ms): {'PASS' if py_pass else 'FAIL'}",
        f"- TMS quality gate (top1>=99%): {'PASS' if tms_pass else 'FAIL'}",
        f"- Reflection gate (success>=99%, p95<50ms): {'PASS' if reflection_pass else 'FAIL'}",
        f"- Phase 4 agentic gate (store/reflection/recall>=99%, p95<120ms): {'PASS' if phase4_pass else 'FAIL'}",
        f"- TypeScript artifacts present: {'YES' if ts_json else 'NO'}",
        f"- Java artifacts present: {'YES' if java_json else 'NO'}",
        "",
        "## Python Wrapper",
        "",
        f"- Regex parse avg: {_fmt(py_spec['regex_parse']['avg_ms'])} ms",
        f"- Regex parse p95: {_fmt(py_spec['regex_parse']['p95_ms'])} ms",
        f"- Regex clean avg: {_fmt(py_spec['regex_clean']['avg_ms'])} ms",
        f"- Regex clean p95: {_fmt(py_spec['regex_clean']['p95_ms'])} ms",
        f"- Exact-case accuracy: {py_acc['exact_case_accuracy_pct']:.2f}%",
        f"- Per-tag accuracy: {py_acc['per_tag_accuracy_pct']:.2f}%",
        "",
        "## TypeScript Wrapper",
        "",
    ]

    if ts_json:
        ts_spec = ts_json["spec_sample"]
        ts_acc = ts_json["accuracy"]
        lines.extend(
            [
                f"- Regex parse avg: {_fmt(ts_spec['regex_parse']['avg_ms'])} ms",
                f"- Regex parse p95: {_fmt(ts_spec['regex_parse']['p95_ms'])} ms",
                f"- Regex clean avg: {_fmt(ts_spec['regex_clean']['avg_ms'])} ms",
                f"- Regex clean p95: {_fmt(ts_spec['regex_clean']['p95_ms'])} ms",
                f"- Exact-case accuracy: {ts_acc['exact_case_accuracy_pct']:.2f}%",
                f"- Per-tag accuracy: {ts_acc['per_tag_accuracy_pct']:.2f}%",
            ]
        )
    else:
        lines.append("- Missing: run `npm run lab:validate` in `typescript/`")

    lines.extend(["", "## Java Wrapper", ""])
    if java_json:
        j_spec = java_json["spec_sample"]
        j_acc = java_json["accuracy"]
        lines.extend(
            [
                f"- Regex parse avg: {_fmt(j_spec['regex_parse']['avg_ms'])} ms",
                f"- Regex parse p95: {_fmt(j_spec['regex_parse']['p95_ms'])} ms",
                f"- Regex clean avg: {_fmt(j_spec['regex_clean']['avg_ms'])} ms",
                f"- Regex clean p95: {_fmt(j_spec['regex_clean']['p95_ms'])} ms",
                f"- Exact-case accuracy: {j_acc['exact_case_accuracy_pct']:.2f}%",
                f"- Per-tag accuracy: {j_acc['per_tag_accuracy_pct']:.2f}%",
            ]
        )
    else:
        lines.append("- Missing: run `mvn -Pbenchmarks verify` in `java/`")

    tms_ops = tms_json["operations"]
    tms_quality = tms_json["quality"]
    lines.extend(
        [
            "",
            "## TMS Core (Python)",
            "",
            f"- Vector backend: {tms_json['metadata']['vector_backend']}",
            f"- Store single avg: {_fmt(tms_ops['store_single']['avg_ms'])} ms",
            f"- Batch store (20) avg: {_fmt(tms_ops['batch_store_20']['avg_ms'])} ms",
            f"- Retrieve filtered avg: {_fmt(tms_ops['retrieve_filtered']['avg_ms'])} ms",
            f"- Semantic search avg: {_fmt(tms_ops['semantic_search']['avg_ms'])} ms",
            f"- Semantic search p95: {_fmt(tms_ops['semantic_search']['p95_ms'])} ms",
            f"- Top-1 exact match: {tms_quality['top1_exact_match_pct']:.2f}%",
            "",
            "## TMS Graph + Reflection (Python)",
            "",
            f"- Graph backend: {graph_json['metadata']['graph_backend']}",
            f"- Add thought avg: {_fmt(graph_json['graph_operations']['add_thought']['avg_ms'])} ms",
            f"- Link avg: {_fmt(graph_json['graph_operations']['link']['avg_ms'])} ms",
            f"- Find paths avg: {_fmt(graph_json['graph_operations']['find_paths']['avg_ms'])} ms",
            f"- Cluster avg: {_fmt(graph_json['graph_operations']['cluster_by_topic']['avg_ms'])} ms",
            f"- Reflection latency avg: {_fmt(graph_json['reflection_cycle']['latency']['avg_ms'])} ms",
            f"- Reflection latency p95: {_fmt(graph_json['reflection_cycle']['latency']['p95_ms'])} ms",
            f"- Reflection success rate: {graph_json['reflection_cycle']['success_rate_pct']:.2f}%",
            "",
            "## Phase 4 Agentic Loop (Python)",
            "",
            f"- Turn total avg: {_fmt(agent['turn_total_latency']['avg_ms'])} ms",
            f"- Turn total p95: {_fmt(agent['turn_total_latency']['p95_ms'])} ms",
            f"- Completion avg: {_fmt(agent['completion_latency']['avg_ms'])} ms",
            f"- Reflection p95: {_fmt(agent['reflection_latency']['p95_ms'])} ms",
            f"- Thought store success rate: {agent['thought_store_success_rate_pct']:.2f}%",
            f"- Reflection success rate: {agent['reflection_success_rate_pct']:.2f}%",
            f"- Recall probe hit rate: {agent['recall_probe_hit_rate_pct']:.2f}%",
            "",
            "## Artifacts",
            "",
            "- Python benchmark: `results/benchmark_results.json`",
            "- TMS benchmark: `results/tms_benchmark_results.json`",
            "- TMS graph benchmark: `results/tms_graph_benchmark_results.json`",
            "- Agent loop benchmark: `results/agent_loop_benchmark_results.json`",
            "- TypeScript benchmark: `typescript/results/benchmark_results.json`",
            "- Java benchmark: `java/results/benchmark_results.json`",
            "",
            "## Python Test Output",
            "",
            "```text",
            py_tests.stdout.strip() or "(no stdout)",
            py_tests.stderr.strip() or "(no stderr)",
            "```",
        ]
    )

    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    sys.stdout.write(py_tests.stdout)
    if py_tests.stderr:
        sys.stderr.write(py_tests.stderr)
    sys.stdout.write(py_bench.stdout)
    if py_bench.stderr:
        sys.stderr.write(py_bench.stderr)
    sys.stdout.write(tms_bench.stdout)
    if tms_bench.stderr:
        sys.stderr.write(tms_bench.stderr)
    sys.stdout.write(graph_bench.stdout)
    if graph_bench.stderr:
        sys.stderr.write(graph_bench.stderr)
    sys.stdout.write(agent_bench.stdout)
    if agent_bench.stderr:
        sys.stderr.write(agent_bench.stderr)
    sys.stdout.write(f"Consolidated report written to {args.report_output}\n")

    if py_tests.returncode != 0:
        return py_tests.returncode
    if not py_pass or not tms_pass or not reflection_pass or not phase4_pass:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
