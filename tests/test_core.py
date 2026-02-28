import unittest

from thought_wrapper import (
    clean_thought_tags,
    clean_thought_tags_linear,
    parse_and_clean,
    parse_thought_tags,
    parse_thought_tags_linear,
)


class TestThoughtWrapperCore(unittest.TestCase):
    def test_parse_extracts_multiple_tags(self) -> None:
        text = "Start /thought[first] Mid /thought[second] End"
        self.assertEqual(
            parse_thought_tags(text),
            {"thought_0": "first", "thought_1": "second"},
        )

    def test_parse_handles_multiline_content(self) -> None:
        text = "A /thought[line1\nline2\nline3] B"
        self.assertEqual(parse_thought_tags(text), {"thought_0": "line1\nline2\nline3"})

    def test_parse_with_custom_tag_name(self) -> None:
        text = "A /fact[x] B /fact[y]"
        self.assertEqual(parse_thought_tags(text, tag_name="fact"), {"fact_0": "x", "fact_1": "y"})

    def test_clean_removes_tags_and_normalizes_whitespace(self) -> None:
        text = "Intro\n\n /thought[a] \n\nBody\n /thought[b]\nOutro"
        cleaned = clean_thought_tags(text)
        self.assertEqual(cleaned, "Intro\nBody\nOutro")

    def test_no_tags_returns_empty_map(self) -> None:
        text = "No tags here."
        self.assertEqual(parse_thought_tags(text), {})
        self.assertEqual(clean_thought_tags(text), "No tags here.")

    def test_unclosed_tag_is_ignored(self) -> None:
        text = "Before /thought[missing close"
        self.assertEqual(parse_thought_tags(text), {})
        self.assertEqual(clean_thought_tags(text), "Before /thought[missing close")

    def test_invalid_tag_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_thought_tags("x", "")
        with self.assertRaises(ValueError):
            clean_thought_tags("x", "   ")

    def test_linear_parser_handles_nested_brackets(self) -> None:
        text = "X /thought[value [with nested] tokens] Y"
        regex_result = parse_thought_tags(text)
        linear_result = parse_thought_tags_linear(text)
        self.assertEqual(regex_result, {"thought_0": "value [with nested"})
        self.assertEqual(linear_result, {"thought_0": "value [with nested] tokens"})

    def test_linear_cleaner_removes_nested_tag(self) -> None:
        text = "Top /thought[a [b] c] Bottom"
        self.assertEqual(clean_thought_tags_linear(text), "Top\nBottom")

    def test_parse_and_clean_convenience(self) -> None:
        text = "Intro /thought[x] Outro"
        cleaned, thoughts = parse_and_clean(text)
        self.assertEqual(cleaned, "Intro\nOutro")
        self.assertEqual(thoughts, {"thought_0": "x"})


if __name__ == "__main__":
    unittest.main()
