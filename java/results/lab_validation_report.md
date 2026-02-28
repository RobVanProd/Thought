# Java Lab Validation Report

- Generated (UTC): 2026-02-28T19:41:21.223663Z
- Method: deterministic JUnit + fuzz + spec reproduction + JMH-backed benchmark + gate checks

## Gate Status

- Unit tests: PASS
- Test count: 16 total, 0 failed
- Spec dictionary reproduction: PASS
- Spec clean-output reproduction: PASS
- Accuracy/latency gates: PASS

## Spec Benchmark

- Input size: 691 chars
- Tag count: 4
- Regex parse avg: 0.013928 ms
- Regex parse p95: 0.016300 ms
- Regex clean avg: 0.011700 ms
- Regex clean p95: 0.018000 ms
- Regex total avg overhead: 0.025628 ms
- Linear parse avg: 0.001143 ms
- Linear clean avg: 0.005567 ms

## Accuracy Study

- Cases: 1000
- Total expected tags: 15339
- Exact-case accuracy: 100.000000%
- Per-tag accuracy: 100.000000%

## Scaling Snapshot

- 693 chars / 4 tags: parse avg 0.009911 ms, clean avg 0.020322 ms
- 10000 chars / 50 tags: parse avg 0.127527 ms, clean avg 0.240816 ms
- 20000 chars / 100 tags: parse avg 0.254240 ms, clean avg 0.479102 ms

## Artifacts

- Benchmark JSON: `results\benchmark_results.json`
- JMH raw JSON: `results\jmh_raw_results.json`
