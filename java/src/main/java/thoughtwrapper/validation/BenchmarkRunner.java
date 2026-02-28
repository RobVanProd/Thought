package thoughtwrapper.validation;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

import org.openjdk.jmh.results.Result;
import org.openjdk.jmh.results.RunResult;
import org.openjdk.jmh.runner.Runner;
import org.openjdk.jmh.runner.RunnerException;
import org.openjdk.jmh.runner.options.Options;
import org.openjdk.jmh.runner.options.OptionsBuilder;
import org.openjdk.jmh.runner.options.TimeValue;
import org.openjdk.jmh.results.format.ResultFormatType;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import thoughtwrapper.Samples;
import thoughtwrapper.ThoughtWrapper;
import thoughtwrapper.bench.ThoughtWrapperBenchmark;

public final class BenchmarkRunner {
    private static final ObjectMapper JSON = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);

    private BenchmarkRunner() {
    }

    public static Map<String, Object> runAndWrite(Path outputPath, int runs, int scaleRuns, int accuracyCases)
            throws IOException, RunnerException {
        Map<String, Object> results = runBenchmark(outputPath, runs, scaleRuns, accuracyCases);
        Files.createDirectories(outputPath.getParent());
        JSON.writeValue(outputPath.toFile(), results);
        return results;
    }

    public static Map<String, Object> runBenchmark(Path outputPath, int runs, int scaleRuns, int accuracyCases)
            throws IOException, RunnerException {
        Path jmhRawPath = outputPath.getParent().resolve("jmh_raw_results.json");
        Map<String, Map<String, Object>> jmhSummary = runJmh(jmhRawPath);

        List<Double> specParse = timeFunction(() -> ThoughtWrapper.parseThoughtTags(Samples.RAW_SPEC_OUTPUT), runs, 200);
        List<Double> specClean = timeFunction(() -> ThoughtWrapper.cleanThoughtTags(Samples.RAW_SPEC_OUTPUT), runs, 200);
        List<Double> specParseLinear = timeFunction(() -> ThoughtWrapper.parseThoughtTagsLinear(Samples.RAW_SPEC_OUTPUT), runs,
                200);
        List<Double> specCleanLinear = timeFunction(() -> ThoughtWrapper.cleanThoughtTagsLinear(Samples.RAW_SPEC_OUTPUT), runs,
                200);

        List<Map<String, Object>> scaling = new ArrayList<>();
        int[][] matrix = new int[][] { { 693, 4, 7 }, { 10_000, 50, 11 }, { 20_000, 100, 19 } };
        for (int[] row : matrix) {
            String text = makeSyntheticOutput(row[0], row[1], row[2]);
            List<Double> parse = timeFunction(() -> ThoughtWrapper.parseThoughtTags(text), scaleRuns, 100);
            List<Double> clean = timeFunction(() -> ThoughtWrapper.cleanThoughtTags(text), scaleRuns, 100);

            Map<String, Object> rowOut = new LinkedHashMap<>();
            rowOut.put("chars", row[0]);
            rowOut.put("tags", row[1]);
            rowOut.put("parse", toStats(parse));
            rowOut.put("clean", toStats(clean));
            scaling.add(rowOut);
        }

        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("timestamp_utc", Instant.now().toString());
        metadata.put("java_version", System.getProperty("java.version"));
        metadata.put("java_vendor", System.getProperty("java.vendor"));
        metadata.put("platform", System.getProperty("os.name") + " " + System.getProperty("os.version"));
        metadata.put("runs", runs);
        metadata.put("scale_runs", scaleRuns);
        metadata.put("accuracy_cases", accuracyCases);
        metadata.put("benchmark_engine", "JMH + nanoTime");

        Map<String, Object> spec = new LinkedHashMap<>();
        spec.put("input_chars", Samples.RAW_SPEC_OUTPUT.length());
        spec.put("tag_count", ThoughtWrapper.parseThoughtTags(Samples.RAW_SPEC_OUTPUT).size());
        spec.put("regex_parse", withJmhStats("thoughtwrapper.bench.ThoughtWrapperBenchmark.specRegexParse", toStats(specParse),
                jmhSummary));
        spec.put("regex_clean", withJmhStats("thoughtwrapper.bench.ThoughtWrapperBenchmark.specRegexClean", toStats(specClean),
                jmhSummary));
        spec.put("linear_parse",
                withJmhStats("thoughtwrapper.bench.ThoughtWrapperBenchmark.specLinearParse", toStats(specParseLinear),
                        jmhSummary));
        spec.put("linear_clean",
                withJmhStats("thoughtwrapper.bench.ThoughtWrapperBenchmark.specLinearClean", toStats(specCleanLinear),
                        jmhSummary));

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("metadata", metadata);
        out.put("spec_sample", spec);
        out.put("scaling", scaling);
        out.put("accuracy", accuracyStudy(accuracyCases, 30));
        out.put("jmh_raw_result_path", outputPath.getParent().resolve("jmh_raw_results.json").toString());
        return out;
    }

    private static Map<String, Map<String, Object>> runJmh(Path outputPath) throws RunnerException, IOException {
        Files.createDirectories(outputPath.getParent());
        Options options = new OptionsBuilder()
                .include(ThoughtWrapperBenchmark.class.getName() + ".*")
                .forks(0)
                .warmupIterations(2)
                .measurementIterations(5)
                .warmupTime(TimeValue.milliseconds(250))
                .measurementTime(TimeValue.milliseconds(250))
                .mode(org.openjdk.jmh.annotations.Mode.AverageTime)
                .timeUnit(TimeUnit.MICROSECONDS)
                .resultFormat(ResultFormatType.JSON)
                .result(outputPath.toString())
                .build();

        Collection<RunResult> results = new Runner(options).run();
        Map<String, Map<String, Object>> out = new LinkedHashMap<>();
        for (RunResult runResult : results) {
            Result<?> primary = runResult.getPrimaryResult();
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("score", primary.getScore());
            row.put("score_error", primary.getScoreError());
            row.put("score_unit", primary.getScoreUnit());
            row.put("label", primary.getLabel());
            out.put(runResult.getParams().getBenchmark(), row);
        }
        return out;
    }

    private static Map<String, Object> withJmhStats(String benchmarkName, Map<String, Object> base,
            Map<String, Map<String, Object>> jmhSummary) {
        Map<String, Object> out = new LinkedHashMap<>(base);
        if (jmhSummary.containsKey(benchmarkName)) {
            out.put("jmh", jmhSummary.get(benchmarkName));
        }
        return out;
    }

    private static List<Double> timeFunction(Supplier<Object> fn, int runs, int warmup) {
        for (int i = 0; i < warmup; i++) {
            fn.get();
        }
        List<Double> samples = new ArrayList<>(runs);
        for (int i = 0; i < runs; i++) {
            long start = System.nanoTime();
            fn.get();
            long end = System.nanoTime();
            samples.add((end - start) / 1_000_000.0);
        }
        return samples;
    }

    private static Map<String, Object> toStats(List<Double> valuesMs) {
        List<Double> ordered = new ArrayList<>(valuesMs);
        ordered.sort(Comparator.naturalOrder());
        int count = ordered.size();
        double sum = 0.0;
        for (double v : ordered) {
            sum += v;
        }
        double avg = sum / count;
        int p50Idx = (int) Math.floor(0.50 * (count - 1));
        int p95Idx = (int) Math.floor(0.95 * (count - 1));
        double variance = 0.0;
        for (double v : ordered) {
            variance += (v - avg) * (v - avg);
        }
        variance /= count;

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("count", count);
        out.put("avg_ms", avg);
        out.put("median_ms", ordered.get(p50Idx));
        out.put("p95_ms", ordered.get(p95Idx));
        out.put("min_ms", ordered.get(0));
        out.put("max_ms", ordered.get(count - 1));
        out.put("std_ms", Math.sqrt(variance));
        return out;
    }

    private static Map<String, Object> accuracyStudy(int cases, int maxTags) {
        Random rng = new Random(20260228L);
        int exactCaseMatches = 0;
        int totalExpectedTags = 0;
        int totalTagsMatched = 0;

        for (int c = 0; c < cases; c++) {
            int tagCount = randomInt(rng, 0, maxTags);
            StringBuilder text = new StringBuilder();
            Map<String, String> expected = new LinkedHashMap<>();
            for (int i = 0; i < tagCount; i++) {
                text.append(randomToken(rng, 0, 20));
                String content = randomToken(rng, 1, 100).replace("]", "");
                text.append("/thought[").append(content).append("]");
                expected.put("thought_" + i, content.trim());
            }
            text.append(randomToken(rng, 0, 20));

            Map<String, String> extracted = ThoughtWrapper.parseThoughtTags(text.toString());
            if (extracted.equals(expected)) {
                exactCaseMatches += 1;
            }
            totalExpectedTags += expected.size();
            for (Map.Entry<String, String> entry : expected.entrySet()) {
                if (entry.getValue().equals(extracted.get(entry.getKey()))) {
                    totalTagsMatched += 1;
                }
            }
        }

        double caseAccuracy = cases > 0 ? (exactCaseMatches * 100.0 / cases) : Double.NaN;
        double tagAccuracy = totalExpectedTags > 0 ? (totalTagsMatched * 100.0 / totalExpectedTags) : 100.0;

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("cases", cases);
        out.put("total_expected_tags", totalExpectedTags);
        out.put("exact_case_accuracy_pct", caseAccuracy);
        out.put("per_tag_accuracy_pct", tagAccuracy);
        return out;
    }

    private static String makeSyntheticOutput(int totalChars, int tagCount, int seed) {
        Random rng = new Random(seed);
        if (tagCount <= 0) {
            return randomText(rng, totalChars);
        }

        int overheadPerTag = "/thought[]\n".length();
        int budgetForPayload = Math.max(0, totalChars - tagCount * overheadPerTag);
        int contentPerTag = Math.max(8, budgetForPayload / tagCount);

        StringBuilder out = new StringBuilder();
        out.append("Synthetic run start.\n");
        for (int i = 0; i < tagCount; i++) {
            out.append(randomText(rng, Math.max(4, contentPerTag / 2)));
            String content = randomText(rng, contentPerTag).replace("]", "");
            out.append("\n/thought[").append(content).append("]\n");
        }
        out.append("Synthetic run end.");
        return out.toString();
    }

    private static String randomText(Random rng, int size) {
        final String alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:-_/\n\t";
        StringBuilder out = new StringBuilder(size);
        for (int i = 0; i < size; i++) {
            out.append(alphabet.charAt(rng.nextInt(alphabet.length())));
        }
        return out.toString();
    }

    private static String randomToken(Random rng, int minLen, int maxLen) {
        int size = randomInt(rng, minLen, maxLen);
        final String alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:-_/\n\t[]()";
        StringBuilder out = new StringBuilder(size);
        for (int i = 0; i < size; i++) {
            out.append(alphabet.charAt(rng.nextInt(alphabet.length())));
        }
        return out.toString().replace("]", "");
    }

    private static int randomInt(Random rng, int min, int max) {
        return min + rng.nextInt(max - min + 1);
    }

    public static String formatDouble(double value) {
        return String.format(Locale.US, "%.6f", value);
    }
}
