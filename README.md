# ThoughtWrapper / Thought Memory System

![Tests](https://img.shields.io/badge/tests-62%2F62%20PASS-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-yellow)

Production-ready explicit thought tagging and persistent LLM memory:

- Multi-language parser/cleaner parity (Python, TypeScript, Java)
- TMS core (typed thought schema, SQLite persistence, hybrid retrieval)
- ThoughtGraph + Reflection Engine
- Multi-model SDK + agentic memory loop
- CLI, FastAPI, Docker templates
- Reproducible lab-grade benchmark and validation protocol

## Installation

```bash
pip install thoughtwrapper
```

## Quickstart (Canonical Commands)

```powershell
cd C:\Users\Rob\projects\Thought
python thought_cli.py --db results/tms_cli.sqlite loop --session demo-1 --input "Assess rollout risk"
docker compose up --build
open http://localhost:8000/docs
python scripts/lab_validate_all.py --python-runs 500 --tms-runs 250 --tms-corpus 1000 --graph-runs 150 --graph-corpus 600 --agent-runs 120 --agent-reflection-frequency 2 --agent-seed-count 30 --report-output results/lab_validation_report.md
python thought_cli.py --db results/tms_cli.sqlite store --session s1 --raw-text "My new thought /thought[planning]"
python thought_cli.py --db results/tms_cli.sqlite retrieve --query "future of memory" --session s1 --limit 5
python thought_cli.py --db results/tms_cli.sqlite reflect --query "future of memory" --session s1 --mode reasoning
```

## Python API

Core parser/cleaner:

```python
from thoughtwrapper import parse_thought_tags, clean_thought_tags

text = "A /thought[first] B"
thoughts = parse_thought_tags(text)        # {'thought_0': 'first'}
cleaned = clean_thought_tags(text)         # 'A\nB'
```

TMS parse -> store -> retrieve:

```python
from thoughtwrapper.tms import ThoughtStore, HashEmbedder, ThoughtFilters
from thoughtwrapper.tms.pipeline import parse_and_store

store = ThoughtStore(db_path="results/tms.sqlite", embedding_dim=384, vector_backend="auto")
embedder = HashEmbedder(dimension=384)

parse_and_store(
    "Intro /thought[Collect benchmark data.] Outro",
    store,
    session_id="demo",
    category="reasoning",
    embedder=embedder,
    embedding_dim=384,
)

hits = store.semantic_search(
    embedder.embed("benchmark data"),
    filters=ThoughtFilters(session_id="demo"),
    limit=5,
)
store.close()
```

## Repository Layout

- `thoughtwrapper/`: public Python namespace
- `thought_wrapper/`: backward-compatible legacy namespace
- `tests/`: deterministic unit tests + fuzz tests
- `scripts/`: benchmark and validation runners
- `typescript/`: TypeScript port (Vitest + Benchmark.js)
- `java/`: Java port (JUnit 5 + JMH)
- `thought_cli.py`, `memory_service.py`, `docker-compose.yml`: runtime/deployment tooling

## Validation

One-command full validation:

```powershell
python scripts/lab_validate_all.py --python-runs 1000 --tms-runs 500 --tms-corpus 1500 --graph-runs 300 --graph-corpus 900 --agent-runs 180 --agent-reflection-frequency 2 --agent-seed-count 40 --report-output results/lab_validation_report.md
```

Primary artifacts:

- `results/lab_validation_report.md`
- `results/benchmark_results.json`
- `results/tms_benchmark_results.json`
- `results/tms_graph_benchmark_results.json`
- `results/agent_loop_benchmark_results.json`

## CI and Releases

- Validation workflow: `.github/workflows/validate.yml`
- Release workflow: `.github/workflows/release.yml` (creates GitHub Release on `v*.*.*` tags)
- Changelog: `CHANGELOG.md` (Keep a Changelog, SemVer)

## License

MIT. See `LICENSE`.
