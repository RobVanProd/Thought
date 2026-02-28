export type ThoughtMap = Record<string, string>;

interface TagMatch {
  start: number;
  end: number;
  content: string;
}

function validateTagName(tagName: string): void {
  if (typeof tagName !== "string" || tagName.trim().length === 0) {
    throw new Error("tag_name must be a non-empty string");
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function parseThoughtTags(text: string, tagName: string = "thought"): ThoughtMap {
  validateTagName(tagName);
  const pattern = new RegExp(`/${escapeRegExp(tagName)}\\[(.*?)\\]`, "gs");
  const thoughts: ThoughtMap = {};
  let idx = 0;
  for (const match of text.matchAll(pattern)) {
    thoughts[`${tagName}_${idx}`] = (match[1] ?? "").trim();
    idx += 1;
  }
  return thoughts;
}

export function cleanThoughtTags(text: string, tagName: string = "thought"): string {
  validateTagName(tagName);
  const pattern = new RegExp(`\\s*/${escapeRegExp(tagName)}\\[.*?\\]\\s*`, "gs");
  const cleaned = text.replace(pattern, "\n");
  return cleaned.replace(/[ \t]+\n/g, "\n").replace(/\n[ \t]+/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
}

function iterTagMatchesLinear(text: string, tagName: string): TagMatch[] {
  const matches: TagMatch[] = [];
  const marker = `/${tagName}[`;
  const markerLen = marker.length;
  let scanIdx = 0;

  while (scanIdx < text.length) {
    const start = text.indexOf(marker, scanIdx);
    if (start < 0) {
      break;
    }
    let cursor = start + markerLen;
    let depth = 1;
    let found = false;

    while (cursor < text.length) {
      const char = text[cursor];
      if (char === "[") {
        depth += 1;
      } else if (char === "]") {
        depth -= 1;
        if (depth === 0) {
          matches.push({
            start,
            end: cursor + 1,
            content: text.slice(start + markerLen, cursor),
          });
          scanIdx = cursor + 1;
          found = true;
          break;
        }
      }
      cursor += 1;
    }

    if (!found) {
      // Unclosed tag: move ahead one char and continue scanning.
      scanIdx = start + 1;
    }
  }

  return matches;
}

export function parseThoughtTagsLinear(text: string, tagName: string = "thought"): ThoughtMap {
  validateTagName(tagName);
  const thoughts: ThoughtMap = {};
  const matches = iterTagMatchesLinear(text, tagName);
  matches.forEach((match, idx) => {
    thoughts[`${tagName}_${idx}`] = match.content.trim();
  });
  return thoughts;
}

export function cleanThoughtTagsLinear(text: string, tagName: string = "thought"): string {
  validateTagName(tagName);
  const matches = iterTagMatchesLinear(text, tagName);
  if (matches.length === 0) {
    return text.replace(/\n{3,}/g, "\n\n").trim();
  }

  const out: string[] = [];
  let cursor = 0;
  for (const match of matches) {
    out.push(text.slice(cursor, match.start));
    out.push("\n");
    cursor = match.end;
  }
  out.push(text.slice(cursor));

  return out.join("").replace(/[ \t]+\n/g, "\n").replace(/\n[ \t]+/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
}

export function parseAndClean(
  text: string,
  tagName: string = "thought",
  linear: boolean = false
): { cleanedText: string; thoughts: ThoughtMap } {
  if (linear) {
    return {
      cleanedText: cleanThoughtTagsLinear(text, tagName),
      thoughts: parseThoughtTagsLinear(text, tagName),
    };
  }
  return {
    cleanedText: cleanThoughtTags(text, tagName),
    thoughts: parseThoughtTags(text, tagName),
  };
}

// Snake_case aliases for explicit spec parity naming.
export const parse_thought_tags = parseThoughtTags;
export const clean_thought_tags = cleanThoughtTags;
export const parse_thought_tags_linear = parseThoughtTagsLinear;
export const clean_thought_tags_linear = cleanThoughtTagsLinear;

