"""Core parser and cleaner implementations for /thought[...] style tags."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class _TagMatch:
    start: int
    end: int
    content: str


def _validate_tag_name(tag_name: str) -> None:
    if not isinstance(tag_name, str) or not tag_name.strip():
        raise ValueError("tag_name must be a non-empty string")


def parse_thought_tags(text: str, tag_name: str = "thought") -> Dict[str, str]:
    """Extracts /<tag_name>[content] markers into a hash map (regex baseline)."""
    _validate_tag_name(tag_name)
    pattern = rf"/{re.escape(tag_name)}\[(.*?)\]"
    matches = re.findall(pattern, text, flags=re.DOTALL)
    thoughts: Dict[str, str] = {}
    for idx, content in enumerate(matches):
        key = f"{tag_name}_{idx}"
        thoughts[key] = content.strip()
    return thoughts


def clean_thought_tags(text: str, tag_name: str = "thought") -> str:
    """Removes /<tag_name>[...] markers and collapses surrounding whitespace."""
    _validate_tag_name(tag_name)
    pattern = rf"\s*/{re.escape(tag_name)}\[.*?\]\s*"
    cleaned = re.sub(pattern, "\n", text, flags=re.DOTALL)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _iter_tag_matches_linear(text: str, tag_name: str) -> Iterable[_TagMatch]:
    marker = f"/{tag_name}["
    marker_len = len(marker)
    scan_idx = 0

    while scan_idx < len(text):
        start = text.find(marker, scan_idx)
        if start < 0:
            break

        cursor = start + marker_len
        depth = 1
        while cursor < len(text):
            char = text[cursor]
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    yield _TagMatch(start=start, end=cursor + 1, content=text[start + marker_len : cursor])
                    scan_idx = cursor + 1
                    break
            cursor += 1
        else:
            # Unclosed tag: skip current slash and continue scanning.
            scan_idx = start + 1


def parse_thought_tags_linear(text: str, tag_name: str = "thought") -> Dict[str, str]:
    """Bracket-balanced linear parser that supports nested brackets in content."""
    _validate_tag_name(tag_name)
    thoughts: Dict[str, str] = {}
    for idx, match in enumerate(_iter_tag_matches_linear(text, tag_name)):
        thoughts[f"{tag_name}_{idx}"] = match.content.strip()
    return thoughts


def clean_thought_tags_linear(text: str, tag_name: str = "thought") -> str:
    """Removes tags using the bracket-balanced parser."""
    _validate_tag_name(tag_name)
    matches = list(_iter_tag_matches_linear(text, tag_name))
    if not matches:
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    out_parts = []
    cursor = 0
    for match in matches:
        out_parts.append(text[cursor : match.start])
        out_parts.append("\n")
        cursor = match.end
    out_parts.append(text[cursor:])

    cleaned = "".join(out_parts)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def parse_and_clean(text: str, tag_name: str = "thought", linear: bool = False) -> tuple[str, Dict[str, str]]:
    """Convenience helper to extract thoughts and return cleaned user-visible text."""
    if linear:
        thoughts = parse_thought_tags_linear(text=text, tag_name=tag_name)
        cleaned = clean_thought_tags_linear(text=text, tag_name=tag_name)
        return cleaned, thoughts
    thoughts = parse_thought_tags(text=text, tag_name=tag_name)
    cleaned = clean_thought_tags(text=text, tag_name=tag_name)
    return cleaned, thoughts

