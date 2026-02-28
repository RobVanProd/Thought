"""Prompt templates for structured thought output and reflection loops."""

from __future__ import annotations

from dataclasses import dataclass


THOUGHT_TAG_GUIDANCE = """Use structured thoughts with XML tags only:
<thought id="unique-id" category="reasoning|fact|plan|reflection" confidence="0.00-1.00">content</thought>
Do not expose hidden reasoning outside <thought> tags.
When key decisions are reached, call reflect() before finalizing the response.
"""

SYSTEM_PROMPT_GENERAL = (
    "You are an analytical assistant with persistent memory. "
    + THOUGHT_TAG_GUIDANCE
    + "\nProduce a concise final answer after thought tags."
)

SYSTEM_PROMPT_CODEX3 = (
    "You are Codex 3 operating with Thought Memory System support. "
    + THOUGHT_TAG_GUIDANCE
    + "\nAt plan milestones, emit thought tags and request reflect() for self-check."
)

REFLECTION_TEMPLATES: dict[str, str] = {
    "reasoning": (
        "Review recalled thoughts and produce 1-3 high-signal reasoning reflections. "
        "Use <thought ...> tags with category='reflection'."
    ),
    "summarization": (
        "Summarize recalled thoughts into actionable memory nuggets. "
        "Use <thought ...> tags with category='summary'."
    ),
    "contradiction_detection": (
        "Detect contradictions or tension between recalled thoughts. "
        "Emit corrected reflections with category='reflection'."
    ),
    "planning": (
        "Convert recalled thoughts into next-step plans. "
        "Use <thought ...> tags with category='plan'."
    ),
}


def build_reflection_prompt(mode: str, query: str, recalled_context: str) -> str:
    if mode not in REFLECTION_TEMPLATES:
        raise ValueError(f"Unsupported reflection mode: {mode}")
    return (
        f"{REFLECTION_TEMPLATES[mode]}\n\n"
        f"Query:\n{query}\n\n"
        f"Recalled Thoughts:\n{recalled_context}\n\n"
        "Return only <thought ...> tags."
    )


EXAMPLE_CONVERSATION_LOOP = """Example loop:
1) recall = store.recall_from_prior_sessions(embed(query), current_session_id, graph=graph)
2) model_output = llm(system_prompt + context)
3) parse_and_store(model_output, store, session_id=current_session_id)
4) reflection = reflection_engine.reflect(query=query, current_session_id=current_session_id, mode="reasoning")
5) continue with updated memory
"""

