"""Empirical benchmark harness for TMS storage and retrieval."""

from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thought_wrapper.tms import HashEmbedder, Thought, ThoughtFilters, ThoughtStore


def _stats(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    n = len(ordered)
    p50 = ordered[int(0.5 * (n - 1))]
    p95 = ordered[int(0.95 * (n - 1))]
    return {
        "count": n,
        "avg_ms": sum(ordered) / n,
        "median_ms": p50,
        "p95_ms": p95,
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "std_ms": statistics.pstdev(ordered) if n > 1 else 0.0,
    }


def _time(fn, runs: int, warmup: int = 100) -> list[float]:
    for _ in range(warmup):
        fn()
    out = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        end = time.perf_counter()
        out.append((end - start) * 1000.0)
    return out


def _build_seeded_thoughts(count: int, embedder: HashEmbedder, *, session_prefix: str) -> list[Thought]:
    rng = random.Random(20260228)
    thoughts: list[Thought] = []
    for i in range(count):
        content = f"thought-{i}-" + "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(16))
        vec = embedder.embed(content)
        thoughts.append(
            Thought(
                session_id=f"{session_prefix}_{i % 10}",
                category="reasoning" if i % 2 == 0 else "fact",
                confidence=0.5 + ((i % 50) / 100.0),
                tags=["seeded", "even" if i % 2 == 0 else "odd"],
                raw_text=content,
                cleaned_text=content,
                embedding_vector=vec,
                embedding_dim=embedder.dimension,
            )
        )
    return thoughts


def run_benchmark(runs: int, corpus_size: int) -> dict[str, object]:
    embedder = HashEmbedder(dimension=384)
    tmp_dir = Path("results/.tmp_tms_bench")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / "tms_bench.sqlite"
    if db_path.exists():
        db_path.unlink()
    store = ThoughtStore(db_path=db_path, embedding_dim=384, vector_backend="auto")
    try:
        base_thoughts = _build_seeded_thoughts(corpus_size, embedder, session_prefix="bench")
        store.batch_store(base_thoughts)

        # Operation benchmarks.
        single_idx = {"value": 0}

        def bench_store_single() -> None:
            i = single_idx["value"]
            single_idx["value"] += 1
            content = f"single-{i}"
            store.store(
                Thought(
                    session_id="single_session",
                    category="reasoning",
                    confidence=0.9,
                    tags=["single"],
                    raw_text=content,
                    cleaned_text=content,
                    embedding_vector=embedder.embed(content),
                    embedding_dim=384,
                )
            )

        batch_idx = {"value": 0}

        def bench_batch_store() -> None:
            i = batch_idx["value"]
            batch_idx["value"] += 1
            batch = []
            for j in range(20):
                content = f"batch-{i}-{j}"
                batch.append(
                    Thought(
                        session_id="batch_session",
                        category="plan",
                        confidence=0.85,
                        tags=["batch"],
                        raw_text=content,
                        cleaned_text=content,
                        embedding_vector=embedder.embed(content),
                        embedding_dim=384,
                    )
                )
            store.batch_store(batch)

        def bench_retrieve() -> None:
            store.retrieve(filters=ThoughtFilters(session_id="bench_1", category="fact"), limit=50)

        query_vec = embedder.embed("thought-42-query-anchor")

        def bench_semantic() -> None:
            store.semantic_search(
                query_vec,
                filters=ThoughtFilters(category="reasoning", min_confidence=0.6),
                limit=20,
                alpha=0.95,
            )

        store_single = _time(bench_store_single, runs=runs, warmup=20)
        batch_store = _time(bench_batch_store, runs=max(100, runs // 2), warmup=10)
        retrieve = _time(bench_retrieve, runs=runs, warmup=50)
        semantic = _time(bench_semantic, runs=runs, warmup=50)

        # Recall quality study: exact top-1 hit where query is exact stored text.
        probe = base_thoughts[:200]
        top1_hits = 0
        for thought in probe:
            result = store.semantic_search(thought.embedding_vector, limit=1, alpha=1.0)
            if result and result[0].thought.id == thought.id:
                top1_hits += 1

        return {
            "metadata": {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "python_version": sys.version.replace("\n", " "),
                "platform": platform.platform(),
                "runs": runs,
                "corpus_size": corpus_size,
                "vector_backend": store.vector_backend_name,
            },
            "operations": {
                "store_single": _stats(store_single),
                "batch_store_20": _stats(batch_store),
                "retrieve_filtered": _stats(retrieve),
                "semantic_search": _stats(semantic),
            },
            "quality": {
                "top1_cases": len(probe),
                "top1_exact_match_pct": (top1_hits / len(probe)) * 100.0 if probe else 0.0,
            },
        }
    finally:
        store.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="TMS benchmark")
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--corpus-size", type=int, default=1500)
    parser.add_argument("--output", type=Path, default=Path("results/tms_benchmark_results.json"))
    args = parser.parse_args()

    result = run_benchmark(runs=args.runs, corpus_size=args.corpus_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    ops = result["operations"]
    quality = result["quality"]
    print("TMS benchmark complete.")
    print(f"Output: {args.output}")
    print(f"Vector backend: {result['metadata']['vector_backend']}")
    print(f"Store single avg (ms): {ops['store_single']['avg_ms']:.6f}")
    print(f"Retrieve filtered avg (ms): {ops['retrieve_filtered']['avg_ms']:.6f}")
    print(f"Semantic search avg (ms): {ops['semantic_search']['avg_ms']:.6f}")
    print(f"Top-1 exact match (%): {quality['top1_exact_match_pct']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
