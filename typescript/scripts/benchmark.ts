import Benchmark from "benchmark";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { performance } from "node:perf_hooks";

import {
  cleanThoughtTags,
  cleanThoughtTagsLinear,
  parseThoughtTags,
  parseThoughtTagsLinear,
} from "../src/core.js";
import { RAW_SPEC_OUTPUT } from "../src/samples.js";

type NumericStats = {
  count: number;
  avg_ms: number;
  median_ms: number;
  p95_ms: number;
  min_ms: number;
  max_ms: number;
  std_ms: number;
};

type CaseStats = NumericStats & {
  hz: number;
  rme_pct: number;
};

function parseArg(flag: string, fallback: string): string {
  const idx = process.argv.indexOf(flag);
  if (idx >= 0 && process.argv[idx + 1]) {
    return process.argv[idx + 1];
  }
  return fallback;
}

function toStats(valuesMs: number[]): NumericStats {
  const ordered = [...valuesMs].sort((a, b) => a - b);
  const count = ordered.length;
  if (count === 0) {
    return {
      count: 0,
      avg_ms: Number.NaN,
      median_ms: Number.NaN,
      p95_ms: Number.NaN,
      min_ms: Number.NaN,
      max_ms: Number.NaN,
      std_ms: Number.NaN,
    };
  }
  const avg = ordered.reduce((acc, v) => acc + v, 0) / count;
  const p = (q: number): number => {
    const idx = Math.floor(q * (count - 1));
    return ordered[idx];
  };
  const variance = ordered.reduce((acc, v) => acc + (v - avg) ** 2, 0) / count;
  return {
    count,
    avg_ms: avg,
    median_ms: p(0.5),
    p95_ms: p(0.95),
    min_ms: ordered[0],
    max_ms: ordered[count - 1],
    std_ms: Math.sqrt(variance),
  };
}

function runBenchmarkCase(name: string, fn: () => void, minSamples = 120, maxTime = 0.35): Promise<CaseStats> {
  return new Promise((resolvePromise, rejectPromise) => {
    const bench = new Benchmark(name, fn, { minSamples, maxTime });
    bench.on("complete", function onComplete(this: Benchmark) {
      const stats = this.stats;
      const sampleSec = stats.sample as number[];
      const msValues =
        sampleSec.length > 0 ? sampleSec.map((v) => v * 1000.0) : [1000.0 / this.hz];
      const aggregate = toStats(msValues);
      resolvePromise({
        ...aggregate,
        hz: this.hz,
        rme_pct: stats.rme,
      });
    });
    bench.on("error", function onError(this: Benchmark, event: unknown) {
      rejectPromise(event);
    });
    bench.run({ async: true });
  });
}

function randomText(seed: number, size: number): string {
  const alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:-_/\n\t";
  let state = seed >>> 0;
  const rand = (): number => {
    state += 0x6d2b79f5;
    let z = state;
    z = Math.imul(z ^ (z >>> 15), z | 1);
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };

  let out = "";
  for (let i = 0; i < size; i += 1) {
    out += alphabet[Math.floor(rand() * alphabet.length)];
  }
  return out;
}

function makeSyntheticOutput(totalChars: number, tagCount: number, seed: number): string {
  if (tagCount <= 0) {
    return randomText(seed, totalChars);
  }
  const overheadPerTag = "/thought[]\n".length;
  const budgetForPayload = Math.max(0, totalChars - tagCount * overheadPerTag);
  const contentPerTag = Math.max(8, Math.floor(budgetForPayload / tagCount));

  const chunks: string[] = ["Synthetic run start.\n"];
  for (let i = 0; i < tagCount; i += 1) {
    chunks.push(randomText(seed + i * 17, Math.max(4, Math.floor(contentPerTag / 2))));
    const content = randomText(seed + i * 31, contentPerTag).replaceAll("]", "");
    chunks.push(`\n/thought[${content}]\n`);
  }
  chunks.push("Synthetic run end.");
  return chunks.join("");
}

function accuracyStudy(cases: number, maxTags = 30): {
  cases: number;
  total_expected_tags: number;
  exact_case_accuracy_pct: number;
  per_tag_accuracy_pct: number;
} {
  let state = 20260228 >>> 0;
  const rand = (): number => {
    state += 0x6d2b79f5;
    let z = state;
    z = Math.imul(z ^ (z >>> 15), z | 1);
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };
  const randomInt = (min: number, max: number): number => Math.floor(rand() * (max - min + 1)) + min;

  let exactCaseMatches = 0;
  let totalExpectedTags = 0;
  let totalTagsMatched = 0;

  for (let c = 0; c < cases; c += 1) {
    const tagCount = randomInt(0, maxTags);
    const expected: Record<string, string> = {};
    const chunks: string[] = [];
    for (let i = 0; i < tagCount; i += 1) {
      chunks.push(randomText(c * 131 + i, randomInt(0, 20)));
      const content = randomText(c * 97 + i, randomInt(1, 100)).replaceAll("]", "");
      chunks.push(`/thought[${content}]`);
      expected[`thought_${i}`] = content.trim();
    }
    chunks.push(randomText(c * 47 + 1, randomInt(0, 20)));
    const text = chunks.join("");
    const extracted = parseThoughtTags(text);

    if (JSON.stringify(extracted) === JSON.stringify(expected)) {
      exactCaseMatches += 1;
    }
    totalExpectedTags += Object.keys(expected).length;
    for (const [key, value] of Object.entries(expected)) {
      if (extracted[key] === value) {
        totalTagsMatched += 1;
      }
    }
  }

  return {
    cases,
    total_expected_tags: totalExpectedTags,
    exact_case_accuracy_pct: cases > 0 ? (exactCaseMatches / cases) * 100.0 : Number.NaN,
    per_tag_accuracy_pct: totalExpectedTags > 0 ? (totalTagsMatched / totalExpectedTags) * 100.0 : 100.0,
  };
}

async function runBenchmark(accuracyCases: number): Promise<Record<string, unknown>> {
  const specParse = await runBenchmarkCase("spec_regex_parse", () => {
    parseThoughtTags(RAW_SPEC_OUTPUT);
  });
  const specClean = await runBenchmarkCase("spec_regex_clean", () => {
    cleanThoughtTags(RAW_SPEC_OUTPUT);
  });
  const specParseLinear = await runBenchmarkCase("spec_linear_parse", () => {
    parseThoughtTagsLinear(RAW_SPEC_OUTPUT);
  });
  const specCleanLinear = await runBenchmarkCase("spec_linear_clean", () => {
    cleanThoughtTagsLinear(RAW_SPEC_OUTPUT);
  });

  const scaleMatrix = [
    { chars: 693, tags: 4, seed: 7 },
    { chars: 10000, tags: 50, seed: 11 },
    { chars: 20000, tags: 100, seed: 19 },
  ];
  const scaling: Array<Record<string, unknown>> = [];
  for (const row of scaleMatrix) {
    const text = makeSyntheticOutput(row.chars, row.tags, row.seed);
    const parseStats = await runBenchmarkCase(`scale_${row.chars}_${row.tags}_parse`, () => {
      parseThoughtTags(text);
    });
    const cleanStats = await runBenchmarkCase(`scale_${row.chars}_${row.tags}_clean`, () => {
      cleanThoughtTags(text);
    });
    scaling.push({
      chars: row.chars,
      tags: row.tags,
      parse: parseStats,
      clean: cleanStats,
    });
  }

  return {
    metadata: {
      timestamp_utc: new Date().toISOString(),
      node_version: process.version,
      platform: process.platform,
      benchmark_engine: "Benchmark.js",
      accuracy_cases: accuracyCases,
    },
    spec_sample: {
      input_chars: RAW_SPEC_OUTPUT.length,
      tag_count: Object.keys(parseThoughtTags(RAW_SPEC_OUTPUT)).length,
      regex_parse: specParse,
      regex_clean: specClean,
      linear_parse: specParseLinear,
      linear_clean: specCleanLinear,
    },
    scaling,
    accuracy: accuracyStudy(accuracyCases),
  };
}

async function main(): Promise<number> {
  const output = resolve(parseArg("--output", "results/benchmark_results.json"));
  const accuracyCases = Number.parseInt(parseArg("--accuracy-cases", "1000"), 10);

  const t0 = performance.now();
  const results = await runBenchmark(accuracyCases);
  const t1 = performance.now();

  mkdirSync(dirname(output), { recursive: true });
  writeFileSync(output, `${JSON.stringify(results, null, 2)}\n`, "utf-8");

  const spec = results.spec_sample as Record<string, any>;
  const accuracy = results.accuracy as Record<string, any>;
  console.log("Benchmark complete.");
  console.log(`Output: ${output}`);
  console.log(`Spec sample chars: ${spec.input_chars}, tags: ${spec.tag_count}`);
  console.log(`Regex parse avg (ms): ${spec.regex_parse.avg_ms.toFixed(6)}`);
  console.log(`Regex clean avg (ms): ${spec.regex_clean.avg_ms.toFixed(6)}`);
  console.log(`Linear parse avg (ms): ${spec.linear_parse.avg_ms.toFixed(6)}`);
  console.log(`Linear clean avg (ms): ${spec.linear_clean.avg_ms.toFixed(6)}`);
  console.log(`Regex parse p95 (ms): ${spec.regex_parse.p95_ms.toFixed(6)}`);
  console.log(`Regex clean p95 (ms): ${spec.regex_clean.p95_ms.toFixed(6)}`);
  console.log(`Exact-case accuracy (%): ${accuracy.exact_case_accuracy_pct.toFixed(2)}`);
  console.log(`Per-tag accuracy (%): ${accuracy.per_tag_accuracy_pct.toFixed(2)}`);
  console.log(`Wall-clock benchmark run time (ms): ${(t1 - t0).toFixed(2)}`);
  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
