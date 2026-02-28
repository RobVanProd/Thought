import {
  cleanThoughtTags,
  cleanThoughtTagsLinear,
  parseAndClean,
  parseThoughtTags,
  parseThoughtTagsLinear,
} from "../src/core.js";
import { describe, expect, test } from "vitest";

describe("core parser and cleaner", () => {
  test("parse extracts multiple tags", () => {
    const text = "Start /thought[first] Mid /thought[second] End";
    expect(parseThoughtTags(text)).toEqual({
      thought_0: "first",
      thought_1: "second",
    });
  });

  test("parse handles multiline content", () => {
    const text = "A /thought[line1\nline2\nline3] B";
    expect(parseThoughtTags(text)).toEqual({
      thought_0: "line1\nline2\nline3",
    });
  });

  test("parse with custom tag", () => {
    const text = "A /fact[x] B /fact[y]";
    expect(parseThoughtTags(text, "fact")).toEqual({
      fact_0: "x",
      fact_1: "y",
    });
  });

  test("clean removes tags and normalizes whitespace", () => {
    const text = "Intro\n\n /thought[a] \n\nBody\n /thought[b]\nOutro";
    expect(cleanThoughtTags(text)).toBe("Intro\nBody\nOutro");
  });

  test("no tags returns empty map", () => {
    const text = "No tags here.";
    expect(parseThoughtTags(text)).toEqual({});
    expect(cleanThoughtTags(text)).toBe("No tags here.");
  });

  test("unclosed tag is ignored", () => {
    const text = "Before /thought[missing close";
    expect(parseThoughtTags(text)).toEqual({});
    expect(cleanThoughtTags(text)).toBe("Before /thought[missing close");
  });

  test("invalid tag name raises", () => {
    expect(() => parseThoughtTags("x", "")).toThrow();
    expect(() => cleanThoughtTags("x", "   ")).toThrow();
  });

  test("linear parser handles nested brackets", () => {
    const text = "X /thought[value [with nested] tokens] Y";
    const regexResult = parseThoughtTags(text);
    const linearResult = parseThoughtTagsLinear(text);
    expect(regexResult).toEqual({ thought_0: "value [with nested" });
    expect(linearResult).toEqual({ thought_0: "value [with nested] tokens" });
  });

  test("linear cleaner removes nested tags", () => {
    const text = "Top /thought[a [b] c] Bottom";
    expect(cleanThoughtTagsLinear(text)).toBe("Top\nBottom");
  });

  test("parse and clean convenience", () => {
    const text = "Intro /thought[x] Outro";
    const out = parseAndClean(text);
    expect(out.cleanedText).toBe("Intro\nOutro");
    expect(out.thoughts).toEqual({ thought_0: "x" });
  });
});
