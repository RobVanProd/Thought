"""Thought tagging wrapper public API."""

from importlib import metadata

from .core import (
    clean_thought_tags,
    clean_thought_tags_linear,
    parse_and_clean,
    parse_thought_tags,
    parse_thought_tags_linear,
)

__all__ = [
    "parse_thought_tags",
    "parse_thought_tags_linear",
    "clean_thought_tags",
    "clean_thought_tags_linear",
    "parse_and_clean",
]

try:
    __version__ = metadata.version("thoughtwrapper")
except metadata.PackageNotFoundError:  # pragma: no cover - local editable source
    __version__ = "1.0.0"

try:
    from .tms import (
        EXAMPLE_CONVERSATION_LOOP,
        HashEmbedder,
        ParseStoreResult,
        REFLECTION_TEMPLATES,
        SYSTEM_PROMPT_CODEX3,
        SYSTEM_PROMPT_GENERAL,
        ScoredThought,
        ReflectionEngine,
        ReflectionResult,
        ThoughtEdge,
        ThoughtGraph,
        SentenceTransformerEmbedder,
        THOUGHT_TAG_GUIDANCE,
        Thought,
        ThoughtFilters,
        ThoughtStore,
        aparse_and_store,
        build_reflection_prompt,
        parse_structured_thoughts,
        parse_and_store as parse_and_store_tms,
    )

    __all__ += [
        "Thought",
        "ThoughtFilters",
        "ScoredThought",
        "ParseStoreResult",
        "ReflectionResult",
        "ThoughtStore",
        "ThoughtEdge",
        "ThoughtGraph",
        "ReflectionEngine",
        "parse_structured_thoughts",
        "HashEmbedder",
        "SentenceTransformerEmbedder",
        "parse_and_store_tms",
        "aparse_and_store",
        "THOUGHT_TAG_GUIDANCE",
        "SYSTEM_PROMPT_GENERAL",
        "SYSTEM_PROMPT_CODEX3",
        "REFLECTION_TEMPLATES",
        "build_reflection_prompt",
        "EXAMPLE_CONVERSATION_LOOP",
    ]
except Exception:
    # Keep core parser/cleaner usable even when optional TMS dependencies are absent.
    pass

try:
    from .agent import AgentLoop, AgentSessionResult, AgentTurnResult
    from .sdk import (
        AnthropicClient,
        ChatMessage,
        LlamaCppClient,
        LLMClient,
        OllamaClient,
        OpenAIClient,
        ThoughtCompletionResult,
        ThoughtLLM,
        ThoughtLLMConfig,
        XAIClient,
    )

    __all__ += [
        "LLMClient",
        "OpenAIClient",
        "AnthropicClient",
        "XAIClient",
        "OllamaClient",
        "LlamaCppClient",
        "ThoughtLLM",
        "ThoughtLLMConfig",
        "ThoughtCompletionResult",
        "ChatMessage",
        "AgentLoop",
        "AgentTurnResult",
        "AgentSessionResult",
    ]
except Exception:
    # SDK/agent exports are optional extensions.
    pass
