"""Sample fixtures used for deterministic reproduction and benchmarking."""

RAW_SPEC_OUTPUT = """Analyzing the feasibility of the /thought tagging system.

 /thought[The regex-based parser is efficient and works on any text output from an LLM, including my own generations.]

 /thought[Testing on myself: I can structure internal reasoning explicitly without changing model behavior.]

 /thought[Extra capability sensed: This enables persistent thought memory across interactions, allowing retrieval of specific reasoning steps for self-correction or learning.]

 /thought[In theory it works perfectly; latency is negligible (<0.01ms); it adds machine-readable structure to otherwise opaque reasoning.]

Final assessment: The system is robust and unlocks human-like metacognition in LLMs."""

EXPECTED_SPEC_THOUGHTS = {
    "thought_0": "The regex-based parser is efficient and works on any text output from an LLM, including my own generations.",
    "thought_1": "Testing on myself: I can structure internal reasoning explicitly without changing model behavior.",
    "thought_2": "Extra capability sensed: This enables persistent thought memory across interactions, allowing retrieval of specific reasoning steps for self-correction or learning.",
    "thought_3": "In theory it works perfectly; latency is negligible (<0.01ms); it adds machine-readable structure to otherwise opaque reasoning.",
}

EXPECTED_SPEC_CLEAN_OUTPUT = """Analyzing the feasibility of the /thought tagging system.

Final assessment: The system is robust and unlocks human-like metacognition in LLMs."""

