package thoughtwrapper;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class ThoughtWrapper {
    private ThoughtWrapper() {
    }

    public static Map<String, String> parseThoughtTags(String text) {
        return parseThoughtTags(text, "thought");
    }

    public static Map<String, String> parseThoughtTags(String text, String tagName) {
        validateTagName(tagName);
        Pattern pattern = Pattern.compile("/" + Pattern.quote(tagName) + "\\[(.*?)]", Pattern.DOTALL);
        Matcher matcher = pattern.matcher(text);
        Map<String, String> thoughts = new LinkedHashMap<>();
        int idx = 0;
        while (matcher.find()) {
            thoughts.put(tagName + "_" + idx, matcher.group(1).trim());
            idx += 1;
        }
        return thoughts;
    }

    public static String cleanThoughtTags(String text) {
        return cleanThoughtTags(text, "thought");
    }

    public static String cleanThoughtTags(String text, String tagName) {
        validateTagName(tagName);
        String pattern = "\\s*/" + Pattern.quote(tagName) + "\\[.*?]\\s*";
        String cleaned = text.replaceAll("(?s)" + pattern, "\n");
        cleaned = cleaned.replaceAll("[ \t]+\n", "\n");
        cleaned = cleaned.replaceAll("\n[ \t]+", "\n");
        cleaned = cleaned.replaceAll("\n{3,}", "\n\n");
        return cleaned.trim();
    }

    public static Map<String, String> parseThoughtTagsLinear(String text) {
        return parseThoughtTagsLinear(text, "thought");
    }

    public static Map<String, String> parseThoughtTagsLinear(String text, String tagName) {
        validateTagName(tagName);
        List<TagMatch> matches = iterTagMatchesLinear(text, tagName);
        Map<String, String> thoughts = new LinkedHashMap<>();
        for (int i = 0; i < matches.size(); i++) {
            thoughts.put(tagName + "_" + i, matches.get(i).content().trim());
        }
        return thoughts;
    }

    public static String cleanThoughtTagsLinear(String text) {
        return cleanThoughtTagsLinear(text, "thought");
    }

    public static String cleanThoughtTagsLinear(String text, String tagName) {
        validateTagName(tagName);
        List<TagMatch> matches = iterTagMatchesLinear(text, tagName);
        if (matches.isEmpty()) {
            return text.replaceAll("\n{3,}", "\n\n").trim();
        }

        StringBuilder out = new StringBuilder();
        int cursor = 0;
        for (TagMatch match : matches) {
            out.append(text, cursor, match.start());
            out.append('\n');
            cursor = match.end();
        }
        out.append(text.substring(cursor));

        String cleaned = out.toString();
        cleaned = cleaned.replaceAll("[ \t]+\n", "\n");
        cleaned = cleaned.replaceAll("\n[ \t]+", "\n");
        cleaned = cleaned.replaceAll("\n{3,}", "\n\n");
        return cleaned.trim();
    }

    public static ParseAndCleanResult parseAndClean(String text, String tagName, boolean linear) {
        if (linear) {
            return new ParseAndCleanResult(cleanThoughtTagsLinear(text, tagName), parseThoughtTagsLinear(text, tagName));
        }
        return new ParseAndCleanResult(cleanThoughtTags(text, tagName), parseThoughtTags(text, tagName));
    }

    public static ParseAndCleanResult parseAndClean(String text) {
        return parseAndClean(text, "thought", false);
    }

    private static List<TagMatch> iterTagMatchesLinear(String text, String tagName) {
        List<TagMatch> matches = new ArrayList<>();
        String marker = "/" + tagName + "[";
        int markerLen = marker.length();
        int scanIdx = 0;

        while (scanIdx < text.length()) {
            int start = text.indexOf(marker, scanIdx);
            if (start < 0) {
                break;
            }
            int cursor = start + markerLen;
            int depth = 1;
            boolean found = false;
            while (cursor < text.length()) {
                char c = text.charAt(cursor);
                if (c == '[') {
                    depth += 1;
                } else if (c == ']') {
                    depth -= 1;
                    if (depth == 0) {
                        matches.add(new TagMatch(start, cursor + 1, text.substring(start + markerLen, cursor)));
                        scanIdx = cursor + 1;
                        found = true;
                        break;
                    }
                }
                cursor += 1;
            }
            if (!found) {
                scanIdx = start + 1;
            }
        }

        return matches;
    }

    private static void validateTagName(String tagName) {
        if (tagName == null || tagName.trim().isEmpty()) {
            throw new IllegalArgumentException("tag_name must be a non-empty string");
        }
    }

    private record TagMatch(int start, int end, String content) {
    }

    public record ParseAndCleanResult(String cleanedText, Map<String, String> thoughts) {
    }
}

