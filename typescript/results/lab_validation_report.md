# TypeScript Lab Validation Report

- Generated (UTC): 2026-02-28T19:41:02.785Z
- Method: deterministic Vitest + fuzz + Benchmark.js empirical timing + gate checks

## Gate Status

- Unit tests: PASS
- Spec dictionary reproduction: PASS
- Spec clean-output reproduction: PASS
- Accuracy/latency gates: PASS

## Spec Benchmark

- Input size: 691 chars
- Tag count: 4
- Regex parse avg: 0.001512 ms
- Regex parse p95: 0.001708 ms
- Regex clean avg: 0.001782 ms
- Regex clean p95: 0.002413 ms
- Regex total avg overhead: 0.003293 ms
- Linear parse avg: 0.001782 ms
- Linear clean avg: 0.002436 ms

## Accuracy Study

- Cases: 1000
- Total expected tags: 14594
- Exact-case accuracy: 100.00%
- Per-tag accuracy: 100.00%

## Scaling Snapshot

- 693 chars / 4 tags: parse avg 0.001616 ms, clean avg 0.001754 ms
- 10000 chars / 50 tags: parse avg 0.013489 ms, clean avg 0.014934 ms
- 20000 chars / 100 tags: parse avg 0.024081 ms, clean avg 0.028634 ms

## Artifacts

- Benchmark JSON: `C:\Users\Rob\projects\Thought\typescript\results\benchmark_results.json`

## Unit Test Output

```text
> thought-wrapper-ts@1.0.0 test
> vitest run --reporter=verbose


[1m[7m[36m RUN [39m[27m[22m [36mv2.1.9 [39m[90mC:/Users/Rob/projects/Thought/typescript[39m

 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22mparse extracts multiple tags
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22mparse handles multiline content
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22mparse with custom tag
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22mclean removes tags and normalizes whitespace
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22mno tags returns empty map
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22munclosed tag is ignored
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22minvalid tag name raises
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22mlinear parser handles nested brackets
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22mlinear cleaner removes nested tags
 [32m✓[39m tests/core.test.ts[2m > [22mcore parser and cleaner[2m > [22mparse and clean convenience
 [32m✓[39m tests/phase4_stub.test.ts[2m > [22mphase4 sdk stub[2m > [22mreturns stable stub metadata
 [32m✓[39m tests/spec_reproduction.test.ts[2m > [22mspec reproduction[2m > [22mexact hash map reproduction
 [32m✓[39m tests/spec_reproduction.test.ts[2m > [22mspec reproduction[2m > [22mexact clean output reproduction
 [32m✓[39m tests/spec_reproduction.test.ts[2m > [22mspec reproduction[2m > [22mlatency is sub-millisecond class for parse and clean averages
 [32m✓[39m tests/fuzz.test.ts[2m > [22mfuzz[2m > [22mrandomized extraction accuracy
 [32m✓[39m tests/fuzz.test.ts[2m > [22mfuzz[2m > [22mclean output has no markers and is idempotent

[2m Test Files [22m [1m[32m4 passed[39m[22m[90m (4)[39m
[2m      Tests [22m [1m[32m16 passed[39m[22m[90m (16)[39m
[2m   Start at [22m 14:39:33
[2m   Duration [22m 558ms[2m (transform 183ms, setup 0ms, collect 274ms, tests 61ms, environment 1ms, prepare 599ms)[22m
(no stderr)
```

## Benchmark Output

```text
> thought-wrapper-ts@1.0.0 benchmark
> tsx scripts/benchmark.ts --output C:\Users\Rob\projects\Thought\typescript\results\benchmark_results.json --accuracy-cases 1000

Benchmark complete.
Output: C:\Users\Rob\projects\Thought\typescript\results\benchmark_results.json
Spec sample chars: 691, tags: 4
Regex parse avg (ms): 0.001512
Regex clean avg (ms): 0.001782
Linear parse avg (ms): 0.001782
Linear clean avg (ms): 0.002436
Regex parse p95 (ms): 0.001708
Regex clean p95 (ms): 0.002413
Exact-case accuracy (%): 100.00
Per-tag accuracy (%): 100.00
Wall-clock benchmark run time (ms): 88313.54
(no stderr)
```
