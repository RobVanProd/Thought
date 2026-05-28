# Thought

Thought's Python test suite passed locally on 2026-05-28: `python -m pytest -q` ran 62 tests in 3.62 seconds with all tests passing.

## What It Is

Thought is an explicit thought-tagging and memory-system prototype for LLM workflows. It includes parsers and cleaners for tagged model output, a SQLite-backed thought store, hybrid retrieval, a directed thought graph, reflection logic, SDK client wrappers, an agent loop, TypeScript and Java artifacts, and benchmark/validation reports under `results/`.

The interesting part is that the repo is built around falsifiable gates: parser accuracy, latency, storage/retrieval behavior, graph behavior, reflection success, and agent-loop behavior are represented in tests and validation artifacts instead of only README prose.

## Current Status

Verified locally:

```bash
python -m pytest -q
```

Result: 62 passed.

The repo also contains a consolidated lab validation report generated on 2026-02-28. That report records passing gates for Python parser/cleaner, TMS quality, reflection, and Phase 4 agent-loop checks, plus latency and accuracy numbers. The local verification above covers the Python pytest suite; it does not re-run TypeScript or Java validation.

## Tech Stack

- Python 3.12+
- SQLite
- NumPy
- Pydantic
- Optional FastAPI service dependency
- TypeScript/Vitest artifacts
- Java artifacts

## Limitations

The `pyproject.toml` still contains placeholder project URLs. The TypeScript and Java artifacts should be revalidated before publishing cross-language claims. This README does not claim package release status.
