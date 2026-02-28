package thoughtwrapper;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;

import org.junit.jupiter.api.Test;

class ThoughtWrapperFuzzTest {
    @Test
    void randomizedExtractionAccuracy() {
        Random rng = new Random(20260228L);
        int totalCases = 400;
        for (int i = 0; i < totalCases; i++) {
            CaseData data = buildCase(rng);
            assertEquals(data.expected(), ThoughtWrapper.parseThoughtTags(data.text()));
        }
    }

    @Test
    void cleanOutputHasNoMarkersAndIsIdempotent() {
        Random rng = new Random(20260228L);
        int totalCases = 250;
        for (int i = 0; i < totalCases; i++) {
            CaseData data = buildCase(rng);
            String cleaned = ThoughtWrapper.cleanThoughtTags(data.text());
            assertFalse(cleaned.contains("/thought["));
            assertEquals(cleaned, ThoughtWrapper.cleanThoughtTags(cleaned));
        }
    }

    private static CaseData buildCase(Random rng) {
        int tagCount = randomInt(rng, 0, 25);
        StringBuilder text = new StringBuilder();
        Map<String, String> expected = new LinkedHashMap<>();
        for (int i = 0; i < tagCount; i++) {
            text.append(randomToken(rng, 0, 32));
            String content = randomToken(rng, 1, 120);
            text.append("/thought[").append(content).append("]");
            expected.put("thought_" + i, content.trim());
        }
        text.append(randomToken(rng, 0, 32));
        return new CaseData(text.toString(), expected);
    }

    private static String randomToken(Random rng, int minLen, int maxLen) {
        String alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:-_/\n\t[]()";
        int size = randomInt(rng, minLen, maxLen);
        StringBuilder out = new StringBuilder(size);
        for (int i = 0; i < size; i++) {
            out.append(alphabet.charAt(rng.nextInt(alphabet.length())));
        }
        return out.toString().replace("]", "");
    }

    private static int randomInt(Random rng, int min, int max) {
        return min + rng.nextInt(max - min + 1);
    }

    private record CaseData(String text, Map<String, String> expected) {
    }
}

