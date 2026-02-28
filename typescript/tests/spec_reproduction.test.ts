import { cleanThoughtTags, parseThoughtTags } from "../src/core.js";
import {
  EXPECTED_SPEC_CLEAN_OUTPUT,
  EXPECTED_SPEC_THOUGHTS,
  RAW_SPEC_OUTPUT,
} from "../src/samples.js";
import { describe, expect, test } from "vitest";

describe("spec reproduction", () => {
  test("exact hash map reproduction", () => {
    expect(parseThoughtTags(RAW_SPEC_OUTPUT)).toEqual(EXPECTED_SPEC_THOUGHTS);
  });

  test("exact clean output reproduction", () => {
    expect(cleanThoughtTags(RAW_SPEC_OUTPUT)).toBe(EXPECTED_SPEC_CLEAN_OUTPUT);
  });

  test("latency is sub-millisecond class for parse and clean averages", () => {
    const runs = 1000;
    let parseTotal = 0;
    let cleanTotal = 0;

    for (let i = 0; i < runs; i += 1) {
      const parseStart = performance.now();
      parseThoughtTags(RAW_SPEC_OUTPUT);
      const parseEnd = performance.now();

      const cleanStart = performance.now();
      cleanThoughtTags(RAW_SPEC_OUTPUT);
      const cleanEnd = performance.now();

      parseTotal += parseEnd - parseStart;
      cleanTotal += cleanEnd - cleanStart;
    }

    const parseAvg = parseTotal / runs;
    const cleanAvg = cleanTotal / runs;
    expect(parseAvg).toBeLessThan(1.0);
    expect(cleanAvg).toBeLessThan(1.0);
  });
});
