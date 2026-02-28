package thoughtwrapper;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

class ThoughtWrapperSpecReproductionTest {
    @Test
    void exactHashMapReproduction() {
        assertEquals(Samples.EXPECTED_SPEC_THOUGHTS, ThoughtWrapper.parseThoughtTags(Samples.RAW_SPEC_OUTPUT));
    }

    @Test
    void exactCleanOutputReproduction() {
        assertEquals(Samples.EXPECTED_SPEC_CLEAN_OUTPUT, ThoughtWrapper.cleanThoughtTags(Samples.RAW_SPEC_OUTPUT));
    }

    @Test
    void latencyIsSubMillisecondClass() {
        int runs = 1000;
        List<Double> parseTimes = new ArrayList<>(runs);
        List<Double> cleanTimes = new ArrayList<>(runs);
        for (int i = 0; i < runs; i++) {
            long parseStart = System.nanoTime();
            ThoughtWrapper.parseThoughtTags(Samples.RAW_SPEC_OUTPUT);
            long parseEnd = System.nanoTime();

            long cleanStart = System.nanoTime();
            ThoughtWrapper.cleanThoughtTags(Samples.RAW_SPEC_OUTPUT);
            long cleanEnd = System.nanoTime();

            parseTimes.add((parseEnd - parseStart) / 1_000_000.0);
            cleanTimes.add((cleanEnd - cleanStart) / 1_000_000.0);
        }
        double parseAvg = parseTimes.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
        double cleanAvg = cleanTimes.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
        assertTrue(parseAvg < 1.0);
        assertTrue(cleanAvg < 1.0);
    }
}

