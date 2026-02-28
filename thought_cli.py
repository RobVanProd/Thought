"""CLI tool for Thought Memory System quick operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from thought_wrapper.agent import AgentLoop
from thought_wrapper.sdk import ThoughtLLM, ThoughtLLMConfig
from thought_wrapper.tms import HashEmbedder, ReflectionEngine, ThoughtFilters, ThoughtGraph, ThoughtStore
from thought_wrapper.tms.pipeline import parse_and_store


class _MockEchoClient:
    provider_name = "mock"

    def complete(self, *, system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int) -> str:
        del system_prompt, model, temperature, max_tokens
        return (
            f'<thought id="mock-1" category="reasoning" confidence="0.92">'
            f"Analyzing: {user_prompt[:120]}"
            "</thought>\n"
            "Final response: processed."
        )


def _make_runtime(db_path: Path, embed_dim: int) -> tuple[ThoughtStore, ThoughtGraph, ReflectionEngine, HashEmbedder]:
    store = ThoughtStore(db_path=db_path, embedding_dim=embed_dim, vector_backend="auto")
    graph = ThoughtGraph(store)
    embedder = HashEmbedder(dimension=embed_dim)
    reflection = ReflectionEngine(store, graph=graph, embedder=embedder, embedding_dim=embed_dim)
    return store, graph, reflection, embedder


def main() -> int:
    parser = argparse.ArgumentParser(description="Thought CLI")
    parser.add_argument("--db", type=Path, default=Path("results/tms_cli.sqlite"))
    parser.add_argument("--embed-dim", type=int, default=384)

    sub = parser.add_subparsers(dest="cmd", required=True)

    store_p = sub.add_parser("store", help="Parse+store raw output")
    store_p.add_argument("--session", required=True)
    store_p.add_argument("--raw-text")
    store_p.add_argument("--raw-file", type=Path)
    store_p.add_argument("--category", default="reasoning")

    retrieve_p = sub.add_parser("retrieve", help="Semantic retrieve")
    retrieve_p.add_argument("--query", required=True)
    retrieve_p.add_argument("--session")
    retrieve_p.add_argument("--limit", type=int, default=10)

    reflect_p = sub.add_parser("reflect", help="Run reflection cycle")
    reflect_p.add_argument("--query", required=True)
    reflect_p.add_argument("--session", required=True)
    reflect_p.add_argument("--mode", default="reasoning")
    reflect_p.add_argument("--top-k", type=int, default=8)

    loop_p = sub.add_parser("loop", help="Run one mock agentic turn")
    loop_p.add_argument("--session", required=True)
    loop_p.add_argument("--input", required=True)

    import_p = sub.add_parser("import-jsonl", help="Batch import JSONL of raw outputs")
    import_p.add_argument("--path", type=Path, required=True)

    args = parser.parse_args()

    store, graph, reflection, embedder = _make_runtime(args.db, args.embed_dim)
    try:
        if args.cmd == "store":
            raw_text = args.raw_text or ""
            if args.raw_file:
                raw_text = args.raw_file.read_text(encoding="utf-8")
            if not raw_text:
                raise ValueError("Provide --raw-text or --raw-file")
            result = parse_and_store(
                raw_text,
                store,
                session_id=args.session,
                category=args.category,
                embedder=embedder,
                embedding_dim=args.embed_dim,
            )
            for thought in result.thoughts:
                graph.add_thought(thought, store_if_missing=False, semantic_neighbors=0)
            print(json.dumps({"stored": len(result.thoughts), "cleaned_output": result.cleaned_output}, indent=2))
            return 0

        if args.cmd == "retrieve":
            vec = embedder.embed(args.query)
            filters = ThoughtFilters(session_id=args.session)
            hits = store.semantic_search(vec, filters=filters, limit=args.limit)
            payload = [
                {
                    "id": h.thought.id,
                    "session_id": h.thought.session_id,
                    "category": h.thought.category,
                    "text": h.thought.cleaned_text,
                    "score": h.score,
                }
                for h in hits
            ]
            print(json.dumps(payload, indent=2))
            return 0

        if args.cmd == "reflect":
            result = reflection.reflect(
                query=args.query,
                current_session_id=args.session,
                mode=args.mode,
                top_k=args.top_k,
            )
            print(
                json.dumps(
                    {
                        "stored_reflections": len(result.stored_reflections),
                        "latency_ms": result.latency_ms,
                        "reflection_text": result.reflection_text,
                    },
                    indent=2,
                )
            )
            return 0

        if args.cmd == "loop":
            llm = ThoughtLLM(
                _MockEchoClient(),
                store=store,
                graph=graph,
                reflection_engine=reflection,
                embedder=embedder,
                config=ThoughtLLMConfig(model="mock", thought_tagging_enforcement="xml"),
            )
            loop = AgentLoop(llm, reflection_frequency=1)
            turn = loop.run_turn(args.input, session_id=args.session)
            print(
                json.dumps(
                    {
                        "cleaned_output": turn.completion.cleaned_output,
                        "stored_thoughts": len(turn.completion.stored_thoughts),
                        "reflected": turn.completion.reflection is not None,
                    },
                    indent=2,
                )
            )
            return 0

        if args.cmd == "import-jsonl":
            count = 0
            for line in args.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                session_id = str(row["session_id"])
                raw_output = str(row["raw_output"])
                result = parse_and_store(
                    raw_output,
                    store,
                    session_id=session_id,
                    category=str(row.get("category", "reasoning")),
                    tags=list(row.get("tags", [])),
                    embedder=embedder,
                    embedding_dim=args.embed_dim,
                )
                for thought in result.thoughts:
                    graph.add_thought(thought, store_if_missing=False, semantic_neighbors=0)
                count += len(result.thoughts)
            print(json.dumps({"imported_thoughts": count}, indent=2))
            return 0

        raise ValueError(f"Unsupported command {args.cmd}")
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())

