package thoughtwrapper;

import java.util.LinkedHashMap;
import java.util.Map;

public final class Samples {
    private Samples() {
    }

    public static final String RAW_SPEC_OUTPUT = """
            Analyzing the feasibility of the /thought tagging system.

             /thought[The regex-based parser is efficient and works on any text output from an LLM, including my own generations.]

             /thought[Testing on myself: I can structure internal reasoning explicitly without changing model behavior.]

             /thought[Extra capability sensed: This enables persistent thought memory across interactions, allowing retrieval of specific reasoning steps for self-correction or learning.]

             /thought[In theory it works perfectly; latency is negligible (<0.01ms); it adds machine-readable structure to otherwise opaque reasoning.]

            Final assessment: The system is robust and unlocks human-like metacognition in LLMs.
            """.stripTrailing();

    public static final Map<String, String> EXPECTED_SPEC_THOUGHTS;

    static {
        Map<String, String> expected = new LinkedHashMap<>();
        expected.put("thought_0",
                "The regex-based parser is efficient and works on any text output from an LLM, including my own generations.");
        expected.put("thought_1",
                "Testing on myself: I can structure internal reasoning explicitly without changing model behavior.");
        expected.put("thought_2",
                "Extra capability sensed: This enables persistent thought memory across interactions, allowing retrieval of specific reasoning steps for self-correction or learning.");
        expected.put("thought_3",
                "In theory it works perfectly; latency is negligible (<0.01ms); it adds machine-readable structure to otherwise opaque reasoning.");
        EXPECTED_SPEC_THOUGHTS = Map.copyOf(expected);
    }

    public static final String EXPECTED_SPEC_CLEAN_OUTPUT = """
            Analyzing the feasibility of the /thought tagging system.

            Final assessment: The system is robust and unlocks human-like metacognition in LLMs.
            """.trim();
}
