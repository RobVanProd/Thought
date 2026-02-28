# Phase 2 Validation Snippets

Generated: 2026-02-28 (UTC)

## 1) Java Port

Artifacts:

- `java/results/benchmark_results.json`
- `java/results/lab_validation_report.md`

Validated outcomes:

- Tests: 15 / 15 PASS
- Exact-case accuracy: 100.00%
- Per-tag accuracy: 100.00%
- Spec regex parse p95: 0.009400 ms
- Spec regex clean p95: 0.011700 ms

## 2) TMS Core (Python)

Artifacts:

- `results/tms_benchmark_results.json`
- `results/lab_validation_report.md` (consolidated)

Validated outcomes:

- Python tests: 25 / 25 PASS (includes TMS deterministic + fuzz tests)
- Semantic top-1 exact match: 100.00%
- Store single avg: 5.396225 ms
- Retrieve filtered avg: 5.058173 ms
- Semantic search avg: 12.736259 ms
