"""Benchmark graph operations and reflection cycle for Phase 3 gates."""

from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thought_wrapper.tms import HashEmbedder, ReflectionEngine, Thought, ThoughtGraph, ThoughtStore


def _stats(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    n = len(ordered)
    return {
        "count": n,
        "avg_ms": sum(ordered) / n,
        "median_ms": ordered[int(0.5 * (n - 1))],
        "p95_ms": ordered[int(0.95 * (n - 1))],
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "std_ms": statistics.pstdev(ordered) if n > 1 else 0.0,
    }


def _time(fn, runs: int, warmup: int = 30) -> list[float]:
    for _ in range(warmup):
        fn()
    out = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        end = time.perf_counter()
        out.append((end - start) * 1000.0)
    return out


def run_benchmark(runs: int, corpus_size: int) -> dict[str, object]:
    embedder = HashEmbedder(dimension=64)
    tmp_dir = Path("results/.tmp_tms_graph")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / "tms_graph_bench.sqlite"
    if db_path.exists():
        db_path.unlink()

    store = ThoughtStore(db_path=db_path, embedding_dim=64, vector_backend="numpy")
    graph = ThoughtGraph(store)
    engine = ReflectionEngine(store, graph=graph, embedder=embedder, embedding_dim=64)
    rng = random.Random(20260228)

    try:
        store.create_session("root")
        store.create_session("child", parent_session_id="root")

        seeded: list[Thought] = []
        now = datetime.now(timezone.utc)
        for i in range(corpus_size):
            text = f"seed-{i}-" + "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(12))
            t = Thought(
                session_id="root" if i % 2 == 0 else "child",
                category="reasoning" if i % 3 else "plan",
                confidence=0.6 + ((i % 20) / 100.0),
                tags=["phase3", "seed"],
                raw_text=text,
                cleaned_text=text,
                embedding_vector=embedder.embed(text),
                embedding_dim=64,
                timestamp_utc=now - timedelta(seconds=(corpus_size - i)),
            )
            graph.add_thought(t, semantic_neighbors=0, temporal_link=True)
            seeded.append(t)

        # Graph operation benches.
        add_idx = {"value": 0}

        def bench_add() -> None:
            i = add_idx["value"]
            add_idx["value"] += 1
            txt = f"bench-add-{i}"
            graph.add_thought(
                Thought(
                    session_id="child",
                    category="reasoning",
                    confidence=0.88,
                    tags=["bench-add"],
                    raw_text=txt,
                    cleaned_text=txt,
                    embedding_vector=embedder.embed(txt),
                    embedding_dim=64,
                ),
                semantic_neighbors=1,
                semantic_threshold=0.92,
                temporal_link=True,
            )

        link_pairs = [(seeded[i].id, seeded[(i + 1) % len(seeded)].id) for i in range(min(400, len(seeded) - 1))]
        link_idx = {"value": 0}

        def bench_link() -> None:
            i = link_idx["value"] % len(link_pairs)
            link_idx["value"] += 1
            src, tgt = link_pairs[i]
            graph.link(src, tgt, relation="explicit-reference", weight=0.8)

        path_pairs = [(seeded[i].id, seeded[min(i + 5, len(seeded) - 1)].id) for i in range(min(200, len(seeded) - 6))]
        path_idx = {"value": 0}

        def bench_paths() -> None:
            i = path_idx["value"] % len(path_pairs)
            path_idx["value"] += 1
            src, tgt = path_pairs[i]
            graph.find_paths(src, tgt, max_depth=5, limit=5)

        def bench_cluster() -> None:
            graph.cluster_by_topic(min_cluster_size=2)

        def bench_temporal_range() -> None:
            end = datetime.now(timezone.utc)
            start = end - timedelta(minutes=15)
            graph.temporal_range(start_time_utc=start, end_time_utc=end, session_id="child", limit=150)

        add_samples = _time(bench_add, runs=max(100, runs // 2), warmup=20)
        link_samples = _time(bench_link, runs=runs, warmup=30)
        path_samples = _time(bench_paths, runs=runs, warmup=30)
        cluster_samples = _time(bench_cluster, runs=max(80, runs // 4), warmup=10)
        temporal_samples = _time(bench_temporal_range, runs=runs, warmup=30)

        # Reflection cycle benchmark + quality.
        reflection_modes = ["reasoning", "summarization", "contradiction_detection", "planning"]
        reflection_latency: list[float] = []
        reflection_success = 0
        reflection_engine = ReflectionEngine(store, graph=None, embedder=embedder, embedding_dim=64)
        store.create_session("reflect_local")
        for i in range(40):
            text = f"reflect-seed-{i}"
            graph.add_thought(
                Thought(
                    session_id="reflect_local",
                    category="reasoning",
                    confidence=0.85,
                    tags=["phase3", "reflect"],
                    raw_text=text,
                    cleaned_text=text,
                    embedding_vector=embedder.embed(text),
                    embedding_dim=64,
                ),
                semantic_neighbors=0,
                temporal_link=False,
            )

        reflection_total = max(60, runs // 3)
        for i in range(reflection_total):
            mode = reflection_modes[i % len(reflection_modes)]
            query = f"phase3-query-{i}"
            result = reflection_engine.reflect(query=query, current_session_id="reflect_local", mode=mode, top_k=3)
            reflection_latency.append(result.latency_ms)
            if result.stored_reflections:
                reflection_success += 1

        return {
            "metadata": {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "python_version": sys.version.replace("\n", " "),
                "platform": platform.platform(),
                "runs": runs,
                "corpus_size": corpus_size,
                "graph_backend": graph.backend_name,
            },
            "graph_operations": {
                "add_thought": _stats(add_samples),
                "link": _stats(link_samples),
                "find_paths": _stats(path_samples),
                "cluster_by_topic": _stats(cluster_samples),
                "temporal_range": _stats(temporal_samples),
            },
            "reflection_cycle": {
                "latency": _stats(reflection_latency),
                "total_cycles": reflection_total,
                "success_cycles": reflection_success,
                "success_rate_pct": (reflection_success / reflection_total) * 100.0 if reflection_total else 0.0,
            },
        }
    finally:
        store.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 graph/reflection benchmark")
    parser.add_argument("--runs", type=int, default=300)
    parser.add_argument("--corpus-size", type=int, default=900)
    parser.add_argument("--output", type=Path, default=Path("results/tms_graph_benchmark_results.json"))
    args = parser.parse_args()

    result = run_benchmark(runs=args.runs, corpus_size=args.corpus_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("TMS graph benchmark complete.")
    print(f"Output: {args.output}")
    print(f"Graph backend: {result['metadata']['graph_backend']}")
    print(f"Add thought avg (ms): {result['graph_operations']['add_thought']['avg_ms']:.6f}")
    print(f"Find paths avg (ms): {result['graph_operations']['find_paths']['avg_ms']:.6f}")
    print(f"Reflection cycle p95 (ms): {result['reflection_cycle']['latency']['p95_ms']:.6f}")
    print(f"Reflection success rate (%): {result['reflection_cycle']['success_rate_pct']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
