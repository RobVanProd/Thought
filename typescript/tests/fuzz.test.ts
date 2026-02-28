import { cleanThoughtTags, parseThoughtTags } from "../src/core.js";
import { describe, expect, test } from "vitest";

function mulberry32(seed: number): () => number {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let z = t;
    z = Math.imul(z ^ (z >>> 15), z | 1);
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };
}

function randomInt(rng: () => number, min: number, max: number): number {
  return Math.floor(rng() * (max - min + 1)) + min;
}

function randomToken(rng: () => number, minLen = 0, maxLen = 32): string {
  const alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:-_/\n\t[]()";
  const len = randomInt(rng, minLen, maxLen);
  let out = "";
  for (let i = 0; i < len; i += 1) {
    out += alphabet[randomInt(rng, 0, alphabet.length - 1)];
  }
  return out.replaceAll("]", "");
}

function buildCase(rng: () => number): { text: string; expected: Record<string, string> } {
  const segments: string[] = [];
  const expected: Record<string, string> = {};
  const tagCount = randomInt(rng, 0, 25);

  for (let i = 0; i < tagCount; i += 1) {
    segments.push(randomToken(rng));
    const content = randomToken(rng, 1, 120);
    segments.push(`/thought[${content}]`);
    expected[`thought_${i}`] = content.trim();
  }
  segments.push(randomToken(rng));
  return { text: segments.join(""), expected };
}

describe("fuzz", () => {
  test("randomized extraction accuracy", () => {
    const rng = mulberry32(20260228);
    const totalCases = 400;
    for (let i = 0; i < totalCases; i += 1) {
      const { text, expected } = buildCase(rng);
      expect(parseThoughtTags(text)).toEqual(expected);
    }
  });

  test("clean output has no markers and is idempotent", () => {
    const rng = mulberry32(20260228);
    const totalCases = 250;
    for (let i = 0; i < totalCases; i += 1) {
      const { text } = buildCase(rng);
      const cleaned = cleanThoughtTags(text);
      expect(cleaned.includes("/thought[")).toBe(false);
      expect(cleanThoughtTags(cleaned)).toBe(cleaned);
    }
  });
});
