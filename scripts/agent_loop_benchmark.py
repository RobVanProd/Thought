"""End-to-end benchmark for Phase 4 agentic memory loop."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thought_wrapper.agent import AgentLoop
from thought_wrapper.sdk import ThoughtLLM, ThoughtLLMConfig
from thought_wrapper.tms import HashEmbedder, ReflectionEngine, Thought, ThoughtGraph, ThoughtStore


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "count": 0,
            "avg_ms": 0.0,
            "median_ms": 0.0,
            "p95_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "std_ms": 0.0,
        }
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


class _BenchmarkClient:
    provider_name = "mock-benchmark"

    def __init__(self) -> None:
        self._counter = 0

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        del system_prompt, user_prompt, model, temperature, max_tokens
        idx = self._counter
        self._counter += 1
        return (
            f'<thought id="bench-{idx}" category="reasoning" confidence="0.91">'
            f"step-{idx} evaluate constraints and update plan"
            "</thought>\n"
            "Final response: loop step complete."
        )


def run_benchmark(runs: int, reflection_frequency: int, seed_count: int) -> dict[str, object]:
    embed_dim = 64
    tmp_dir = Path("results/.tmp_agent_loop_bench")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / "agent_loop.sqlite"
    if db_path.exists():
        db_path.unlink()

    store = ThoughtStore(db_path=db_path, embedding_dim=embed_dim, vector_backend="numpy")
    graph = ThoughtGraph(store)
    embedder = HashEmbedder(dimension=embed_dim)
    reflection = ReflectionEngine(store, graph=graph, embedder=embedder, embedding_dim=embed_dim)
    client = _BenchmarkClient()

    llm = ThoughtLLM(
        client,
        store=store,
        graph=graph,
        reflection_engine=reflection,
        embedder=embedder,
        config=ThoughtLLMConfig(
            model="mock-phase4",
            thought_tagging_enforcement="xml",
            reflect_enabled=True,
            reflection_frequency=1,
            recall_top_k=max(80, seed_count + 20),
        ),
    )
    loop = AgentLoop(llm, reflection_frequency=max(1, reflection_frequency))

    try:
        # Seed parent session with anchor memories used by recall probes.
        store.create_session("phase4_parent")
        store.create_session("phase4_child", parent_session_id="phase4_parent")
        for i in range(seed_count):
            text = f"root-anchor-{i}: critical prior memory {i}"
            graph.add_thought(
                Thought(
                    session_id="phase4_parent",
                    category="fact",
                    confidence=0.93,
                    tags=["seed", "phase4"],
                    raw_text=text,
                    cleaned_text=text,
                    embedding_vector=embedder.embed(text),
                    embedding_dim=embed_dim,
                ),
                semantic_neighbors=0,
                temporal_link=False,
            )

        turn_total_latency: list[float] = []
        completion_latency: list[float] = []
        reflection_latency: list[float] = []

        stored_success = 0
        reflection_expected = 0
        reflection_success = 0
        recall_probe_total = 0
        recall_probe_hits = 0

        for i in range(runs):
            probe = i % 3 == 0
            if probe:
                recall_probe_total += 1
                prompt = f"Need context for root-anchor-{i % seed_count}"
            else:
                prompt = f"Operational update request turn {i}"

            start = time.perf_counter()
            turn = loop.run_turn(
                prompt,
                session_id="phase4_child",
                parent_session_id="phase4_parent",
            )
            end = time.perf_counter()

            total_ms = (end - start) * 1000.0
            turn_total_latency.append(total_ms)
            completion_latency.append(turn.completion.latency_ms)

            if turn.completion.stored_thoughts:
                stored_success += 1

            if turn.turn_index % max(1, reflection_frequency) == 0:
                reflection_expected += 1
                if turn.completion.reflection and turn.completion.reflection.stored_reflections:
                    reflection_success += 1
                    reflection_latency.append(turn.completion.reflection.latency_ms)

            if probe:
                has_parent_recall = any(item.session_id == "phase4_parent" for item in turn.completion.recalled_context)
                if has_parent_recall:
                    recall_probe_hits += 1

        return {
            "metadata": {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "python_version": sys.version.replace("\n", " "),
                "platform": platform.platform(),
                "runs": runs,
                "seed_count": seed_count,
                "reflection_frequency": reflection_frequency,
            },
            "agentic_loop": {
                "turn_total_latency": _stats(turn_total_latency),
                "completion_latency": _stats(completion_latency),
                "reflection_latency": _stats(reflection_latency),
                "thought_store_success_rate_pct": (stored_success / runs) * 100.0 if runs else 0.0,
                "reflection_success_rate_pct": (
                    (reflection_success / reflection_expected) * 100.0 if reflection_expected else 100.0
                ),
                "recall_probe_total": recall_probe_total,
                "recall_probe_hit_rate_pct": (
                    (recall_probe_hits / recall_probe_total) * 100.0 if recall_probe_total else 100.0
                ),
            },
        }
    finally:
        store.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4 agentic loop benchmark")
    parser.add_argument("--runs", type=int, default=180)
    parser.add_argument("--reflection-frequency", type=int, default=2)
    parser.add_argument("--seed-count", type=int, default=40)
    parser.add_argument("--output", type=Path, default=Path("results/agent_loop_benchmark_results.json"))
    args = parser.parse_args()

    result = run_benchmark(
        runs=args.runs,
        reflection_frequency=max(1, args.reflection_frequency),
        seed_count=max(1, args.seed_count),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    section = result["agentic_loop"]
    print("Agentic loop benchmark complete.")
    print(f"Output: {args.output}")
    print(f"Turn total avg (ms): {section['turn_total_latency']['avg_ms']:.6f}")
    print(f"Turn total p95 (ms): {section['turn_total_latency']['p95_ms']:.6f}")
    print(f"Reflection p95 (ms): {section['reflection_latency']['p95_ms']:.6f}")
    print(f"Thought store success (%): {section['thought_store_success_rate_pct']:.2f}")
    print(f"Recall probe hit rate (%): {section['recall_probe_hit_rate_pct']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
