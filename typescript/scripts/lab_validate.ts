import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";

import { cleanThoughtTags, parseThoughtTags } from "../src/core.js";
import {
  EXPECTED_SPEC_CLEAN_OUTPUT,
  EXPECTED_SPEC_THOUGHTS,
  RAW_SPEC_OUTPUT,
} from "../src/samples.js";

function parseArg(flag: string, fallback: string): string {
  const idx = process.argv.indexOf(flag);
  if (idx >= 0 && process.argv[idx + 1]) {
    return process.argv[idx + 1];
  }
  return fallback;
}

function runCommand(command: string): { code: number; stdout: string; stderr: string } {
  const result = spawnSync(command, {
    cwd: process.cwd(),
    shell: true,
    encoding: "utf-8",
  });
  return {
    code: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function formatNum(value: number): string {
  return Number.isFinite(value) ? value.toFixed(6) : "NaN";
}

function gateStatus(benchmark: any): { pass: boolean; reasons: string[] } {
  const reasons: string[] = [];
  const acc = benchmark.accuracy;
  const spec = benchmark.spec_sample;

  if (acc.exact_case_accuracy_pct < 99.9) {
    reasons.push(`exact-case accuracy ${acc.exact_case_accuracy_pct.toFixed(3)}% < 99.9%`);
  }
  if (acc.per_tag_accuracy_pct < 99.9) {
    reasons.push(`per-tag accuracy ${acc.per_tag_accuracy_pct.toFixed(3)}% < 99.9%`);
  }
  if (spec.regex_parse.p95_ms >= 1.0) {
    reasons.push(`regex parse p95 ${spec.regex_parse.p95_ms.toFixed(6)} ms >= 1.0 ms`);
  }
  if (spec.regex_clean.p95_ms >= 1.0) {
    reasons.push(`regex clean p95 ${spec.regex_clean.p95_ms.toFixed(6)} ms >= 1.0 ms`);
  }
  return { pass: reasons.length === 0, reasons };
}

function main(): number {
  const benchmarkOutput = resolve(parseArg("--benchmark-output", "results/benchmark_results.json"));
  const reportOutput = resolve(parseArg("--report-output", "results/lab_validation_report.md"));
  const accuracyCases = parseArg("--accuracy-cases", "1000");

  const testRun = runCommand("npm run test");
  const benchmarkRun = runCommand(`npm run benchmark -- --output "${benchmarkOutput}" --accuracy-cases ${accuracyCases}`);

  if (benchmarkRun.code !== 0) {
    process.stdout.write(benchmarkRun.stdout);
    process.stderr.write(benchmarkRun.stderr);
    return benchmarkRun.code;
  }

  const benchmark = JSON.parse(readFileSync(benchmarkOutput, "utf-8"));
  const specDictOk = JSON.stringify(parseThoughtTags(RAW_SPEC_OUTPUT)) === JSON.stringify(EXPECTED_SPEC_THOUGHTS);
  const specCleanOk = cleanThoughtTags(RAW_SPEC_OUTPUT) === EXPECTED_SPEC_CLEAN_OUTPUT;
  const gates = gateStatus(benchmark);

  const spec = benchmark.spec_sample;
  const accuracy = benchmark.accuracy;
  const lines = [
    "# TypeScript Lab Validation Report",
    "",
    `- Generated (UTC): ${new Date().toISOString()}`,
    "- Method: deterministic Vitest + fuzz + Benchmark.js empirical timing + gate checks",
    "",
    "## Gate Status",
    "",
    `- Unit tests: ${testRun.code === 0 ? "PASS" : "FAIL"}`,
    `- Spec dictionary reproduction: ${specDictOk ? "PASS" : "FAIL"}`,
    `- Spec clean-output reproduction: ${specCleanOk ? "PASS" : "FAIL"}`,
    `- Accuracy/latency gates: ${gates.pass ? "PASS" : "FAIL"}`,
    "",
    "## Spec Benchmark",
    "",
    `- Input size: ${spec.input_chars} chars`,
    `- Tag count: ${spec.tag_count}`,
    `- Regex parse avg: ${formatNum(spec.regex_parse.avg_ms)} ms`,
    `- Regex parse p95: ${formatNum(spec.regex_parse.p95_ms)} ms`,
    `- Regex clean avg: ${formatNum(spec.regex_clean.avg_ms)} ms`,
    `- Regex clean p95: ${formatNum(spec.regex_clean.p95_ms)} ms`,
    `- Regex total avg overhead: ${formatNum(spec.regex_parse.avg_ms + spec.regex_clean.avg_ms)} ms`,
    `- Linear parse avg: ${formatNum(spec.linear_parse.avg_ms)} ms`,
    `- Linear clean avg: ${formatNum(spec.linear_clean.avg_ms)} ms`,
    "",
    "## Accuracy Study",
    "",
    `- Cases: ${accuracy.cases}`,
    `- Total expected tags: ${accuracy.total_expected_tags}`,
    `- Exact-case accuracy: ${accuracy.exact_case_accuracy_pct.toFixed(2)}%`,
    `- Per-tag accuracy: ${accuracy.per_tag_accuracy_pct.toFixed(2)}%`,
    "",
    "## Scaling Snapshot",
    "",
  ];

  for (const row of benchmark.scaling) {
    lines.push(
      `- ${row.chars} chars / ${row.tags} tags: parse avg ${formatNum(row.parse.avg_ms)} ms, clean avg ${formatNum(
        row.clean.avg_ms
      )} ms`
    );
  }

  if (!gates.pass) {
    lines.push("", "## Gate Fail Reasons", "");
    gates.reasons.forEach((reason) => lines.push(`- ${reason}`));
  }

  lines.push(
    "",
    "## Artifacts",
    "",
    `- Benchmark JSON: \`${benchmarkOutput}\``,
    "",
    "## Unit Test Output",
    "",
    "```text",
    testRun.stdout.trim() || "(no stdout)",
    testRun.stderr.trim() || "(no stderr)",
    "```",
    "",
    "## Benchmark Output",
    "",
    "```text",
    benchmarkRun.stdout.trim() || "(no stdout)",
    benchmarkRun.stderr.trim() || "(no stderr)",
    "```"
  );

  mkdirSync(dirname(reportOutput), { recursive: true });
  writeFileSync(reportOutput, `${lines.join("\n")}\n`, "utf-8");

  process.stdout.write(testRun.stdout);
  process.stderr.write(testRun.stderr);
  process.stdout.write(benchmarkRun.stdout);
  process.stderr.write(benchmarkRun.stderr);
  process.stdout.write(`Report written to ${reportOutput}\n`);

  if (testRun.code !== 0) {
    return testRun.code;
  }
  if (!specDictOk || !specCleanOk || !gates.pass) {
    return 2;
  }
  return 0;
}

process.exit(main());
