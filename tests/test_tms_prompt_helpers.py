import unittest

from thought_wrapper.tms.prompt_helpers import (
    EXAMPLE_CONVERSATION_LOOP,
    REFLECTION_TEMPLATES,
    SYSTEM_PROMPT_CODEX3,
    SYSTEM_PROMPT_GENERAL,
    build_reflection_prompt,
)


class TestTmsPromptHelpers(unittest.TestCase):
    def test_templates_exist(self) -> None:
        self.assertIn("reasoning", REFLECTION_TEMPLATES)
        self.assertIn("planning", REFLECTION_TEMPLATES)

    def test_build_prompt(self) -> None:
        prompt = build_reflection_prompt("reasoning", "q", "- a")
        self.assertIn("Query:", prompt)
        self.assertIn("Return only <thought", prompt)

    def test_system_prompts_include_tag_guidance(self) -> None:
        self.assertIn("<thought id=", SYSTEM_PROMPT_GENERAL)
        self.assertIn("reflect()", SYSTEM_PROMPT_CODEX3)
        self.assertIn("recall", EXAMPLE_CONVERSATION_LOOP)


if __name__ == "__main__":
    unittest.main()

