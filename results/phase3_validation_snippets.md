# Phase 3 Validation Snippets

Generated: 2026-02-28 (UTC)

## New Gates

- Reflection cycle success rate: 100.00% (threshold >= 99.00%)
- Reflection cycle p95 latency: 46.233900 ms (threshold < 50.000000 ms)

## Python + TMS + Graph

- Python tests: 41 / 41 PASS
- Parser exact-case accuracy: 100.00%
- Parser per-tag accuracy: 100.00%
- TMS top-1 exact match: 100.00%
- TMS store single avg: 3.964107 ms
- TMS semantic search avg: 12.045792 ms
- Graph add-thought avg: 22.378972 ms
- Graph find-paths avg: 1.412663 ms

## Cross-Language Status

- TypeScript parser/cleaner gates: PASS
- Java parser/cleaner gates: PASS
- TypeScript Phase 3 stub present: `typescript/src/tms/phase3_stub.ts`
- Java Phase 3 stub present: `java/src/main/java/thoughtwrapper/tms/Phase3Stub.java`
