import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function parseArg(flag: string, fallback: string): string {
  const idx = process.argv.indexOf(flag);
  if (idx >= 0 && process.argv[idx + 1]) {
    return process.argv[idx + 1];
  }
  return fallback;
}

function main(): number {
  const input = resolve(parseArg("--input", "results/benchmark_results.json"));
  const minAccuracy = Number.parseFloat(parseArg("--min-accuracy", "99.9"));
  const maxP95 = Number.parseFloat(parseArg("--max-p95-ms", "1.0"));

  const data = JSON.parse(readFileSync(input, "utf-8"));
  const accuracy = data.accuracy;
  const spec = data.spec_sample;

  const failures: string[] = [];
  if (accuracy.exact_case_accuracy_pct < minAccuracy) {
    failures.push(`exact-case accuracy ${accuracy.exact_case_accuracy_pct.toFixed(6)}% < ${minAccuracy.toFixed(3)}%`);
  }
  if (accuracy.per_tag_accuracy_pct < minAccuracy) {
    failures.push(`per-tag accuracy ${accuracy.per_tag_accuracy_pct.toFixed(6)}% < ${minAccuracy.toFixed(3)}%`);
  }
  if (spec.regex_parse.p95_ms >= maxP95) {
    failures.push(`regex parse p95 ${spec.regex_parse.p95_ms.toFixed(6)} ms >= ${maxP95.toFixed(6)} ms`);
  }
  if (spec.regex_clean.p95_ms >= maxP95) {
    failures.push(`regex clean p95 ${spec.regex_clean.p95_ms.toFixed(6)} ms >= ${maxP95.toFixed(6)} ms`);
  }

  if (failures.length > 0) {
    console.error("CI gates: FAIL");
    failures.forEach((failure) => console.error(`- ${failure}`));
    return 1;
  }

  console.log("CI gates: PASS");
  console.log(`- exact-case accuracy: ${accuracy.exact_case_accuracy_pct.toFixed(6)}%`);
  console.log(`- per-tag accuracy: ${accuracy.per_tag_accuracy_pct.toFixed(6)}%`);
  console.log(`- regex parse p95: ${spec.regex_parse.p95_ms.toFixed(6)} ms`);
  console.log(`- regex clean p95: ${spec.regex_clean.p95_ms.toFixed(6)} ms`);
  return 0;
}

process.exit(main());

