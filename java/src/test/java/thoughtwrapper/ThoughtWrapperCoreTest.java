package thoughtwrapper;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

class ThoughtWrapperCoreTest {
    @Test
    void parseExtractsMultipleTags() {
        String text = "Start /thought[first] Mid /thought[second] End";
        Map<String, String> expected = new LinkedHashMap<>();
        expected.put("thought_0", "first");
        expected.put("thought_1", "second");
        assertEquals(expected, ThoughtWrapper.parseThoughtTags(text));
    }

    @Test
    void parseHandlesMultilineContent() {
        String text = "A /thought[line1\nline2\nline3] B";
        Map<String, String> expected = Map.of("thought_0", "line1\nline2\nline3");
        assertEquals(expected, ThoughtWrapper.parseThoughtTags(text));
    }

    @Test
    void parseWithCustomTagName() {
        String text = "A /fact[x] B /fact[y]";
        Map<String, String> expected = new LinkedHashMap<>();
        expected.put("fact_0", "x");
        expected.put("fact_1", "y");
        assertEquals(expected, ThoughtWrapper.parseThoughtTags(text, "fact"));
    }

    @Test
    void cleanRemovesTagsAndNormalizesWhitespace() {
        String text = "Intro\n\n /thought[a] \n\nBody\n /thought[b]\nOutro";
        assertEquals("Intro\nBody\nOutro", ThoughtWrapper.cleanThoughtTags(text));
    }

    @Test
    void noTagsReturnsEmptyMap() {
        String text = "No tags here.";
        assertEquals(Map.of(), ThoughtWrapper.parseThoughtTags(text));
        assertEquals("No tags here.", ThoughtWrapper.cleanThoughtTags(text));
    }

    @Test
    void unclosedTagIsIgnored() {
        String text = "Before /thought[missing close";
        assertEquals(Map.of(), ThoughtWrapper.parseThoughtTags(text));
        assertEquals("Before /thought[missing close", ThoughtWrapper.cleanThoughtTags(text));
    }

    @Test
    void invalidTagNameRaises() {
        assertThrows(IllegalArgumentException.class, () -> ThoughtWrapper.parseThoughtTags("x", ""));
        assertThrows(IllegalArgumentException.class, () -> ThoughtWrapper.cleanThoughtTags("x", "  "));
    }

    @Test
    void linearParserHandlesNestedBrackets() {
        String text = "X /thought[value [with nested] tokens] Y";
        Map<String, String> regex = ThoughtWrapper.parseThoughtTags(text);
        Map<String, String> linear = ThoughtWrapper.parseThoughtTagsLinear(text);
        assertEquals(Map.of("thought_0", "value [with nested"), regex);
        assertEquals(Map.of("thought_0", "value [with nested] tokens"), linear);
    }

    @Test
    void linearCleanerRemovesNestedTag() {
        String text = "Top /thought[a [b] c] Bottom";
        assertEquals("Top\nBottom", ThoughtWrapper.cleanThoughtTagsLinear(text));
    }

    @Test
    void parseAndCleanConvenience() {
        String text = "Intro /thought[x] Outro";
        var out = ThoughtWrapper.parseAndClean(text);
        assertEquals("Intro\nOutro", out.cleanedText());
        assertEquals(Map.of("thought_0", "x"), out.thoughts());
    }
}

