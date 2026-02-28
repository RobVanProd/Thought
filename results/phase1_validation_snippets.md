# Phase 1 Validation Snippets

Generated: 2026-02-28 (UTC)

## a) TypeScript Port

Artifacts:

- `typescript/results/benchmark_results.json`
- `typescript/results/lab_validation_report.md`

Key metrics:

- Unit tests: 15 / 15 PASS
- Exact-case accuracy: 100.00%
- Per-tag accuracy: 100.00%
- Spec regex parse avg: 0.001476 ms
- Spec regex clean avg: 0.001528 ms
- Spec regex parse p95: 0.001567 ms
- Spec regex clean p95: 0.001651 ms

Lab report excerpt:

```text
## Gate Status
- Unit tests: PASS
- Spec dictionary reproduction: PASS
- Spec clean-output reproduction: PASS
- Accuracy/latency gates: PASS
```

## b) CI Gates

Artifacts:

- `.github/workflows/validate.yml`
- `scripts/check_gates.py`
- `typescript/scripts/check_gates.ts`

Local gate-check outputs:

```text
Python:
CI gates: PASS
- exact-case accuracy: 100.000000%
- per-tag accuracy: 100.000000%
- regex parse p95: 0.006600 ms
- regex clean p95: 0.010900 ms

TypeScript:
CI gates: PASS
- exact-case accuracy: 100.000000%
- per-tag accuracy: 100.000000%
- regex parse p95: 0.001567 ms
- regex clean p95: 0.001651 ms
```
