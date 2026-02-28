package thoughtwrapper.validation;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import javax.xml.parsers.DocumentBuilderFactory;

import org.openjdk.jmh.runner.RunnerException;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import thoughtwrapper.Samples;
import thoughtwrapper.ThoughtWrapper;

public final class LabValidate {
    private static final ObjectMapper JSON = new ObjectMapper();

    private LabValidate() {
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> parsedArgs = parseArgs(args);
        Path benchmarkOutput = Path
                .of(parsedArgs.getOrDefault("--benchmark-output", "results/benchmark_results.json"));
        Path reportOutput = Path.of(parsedArgs.getOrDefault("--report-output", "results/lab_validation_report.md"));
        int runs = Integer.parseInt(parsedArgs.getOrDefault("--runs", "1000"));
        int scaleRuns = Integer.parseInt(parsedArgs.getOrDefault("--scale-runs", "1000"));
        int accuracyCases = Integer.parseInt(parsedArgs.getOrDefault("--accuracy-cases", "1000"));

        Map<String, Object> benchmark = BenchmarkRunner.runAndWrite(benchmarkOutput, runs, scaleRuns, accuracyCases);

        TestSummary testSummary = readSurefireSummary(Path.of("target", "surefire-reports"));
        boolean specDictOk = ThoughtWrapper.parseThoughtTags(Samples.RAW_SPEC_OUTPUT).equals(Samples.EXPECTED_SPEC_THOUGHTS);
        boolean specCleanOk = ThoughtWrapper.cleanThoughtTags(Samples.RAW_SPEC_OUTPUT)
                .equals(Samples.EXPECTED_SPEC_CLEAN_OUTPUT);
        GateCheck gates = evaluateGates(benchmark, 99.9, 1.0);

        writeReport(reportOutput, benchmarkOutput, benchmark, testSummary, specDictOk, specCleanOk, gates);

        System.out.println("Benchmark complete.");
        System.out.println("Output: " + benchmarkOutput.toAbsolutePath());
        Map<String, Object> spec = asMap(benchmark.get("spec_sample"));
        Map<String, Object> accuracy = asMap(benchmark.get("accuracy"));
        System.out.println("Spec sample chars: " + spec.get("input_chars") + ", tags: " + spec.get("tag_count"));
        System.out.println("Regex parse avg (ms): "
                + BenchmarkRunner.formatDouble(((Number) asMap(spec.get("regex_parse")).get("avg_ms")).doubleValue()));
        System.out.println("Regex clean avg (ms): "
                + BenchmarkRunner.formatDouble(((Number) asMap(spec.get("regex_clean")).get("avg_ms")).doubleValue()));
        System.out.println("Regex parse p95 (ms): "
                + BenchmarkRunner.formatDouble(((Number) asMap(spec.get("regex_parse")).get("p95_ms")).doubleValue()));
        System.out.println("Regex clean p95 (ms): "
                + BenchmarkRunner.formatDouble(((Number) asMap(spec.get("regex_clean")).get("p95_ms")).doubleValue()));
        System.out.println("Exact-case accuracy (%): "
                + BenchmarkRunner.formatDouble(((Number) accuracy.get("exact_case_accuracy_pct")).doubleValue()));
        System.out.println("Per-tag accuracy (%): "
                + BenchmarkRunner.formatDouble(((Number) accuracy.get("per_tag_accuracy_pct")).doubleValue()));
        System.out.println("Report written to " + reportOutput.toAbsolutePath());

        if (!testSummary.pass || !specDictOk || !specCleanOk || !gates.pass) {
            System.exit(2);
        }
    }

    public static GateCheck evaluateGates(Map<String, Object> benchmark, double minAccuracy, double maxP95Ms) {
        Map<String, Object> accuracy = asMap(benchmark.get("accuracy"));
        Map<String, Object> spec = asMap(benchmark.get("spec_sample"));
        Map<String, Object> regexParse = asMap(spec.get("regex_parse"));
        Map<String, Object> regexClean = asMap(spec.get("regex_clean"));

        List<String> reasons = new ArrayList<>();
        double exactCaseAccuracy = ((Number) accuracy.get("exact_case_accuracy_pct")).doubleValue();
        double perTagAccuracy = ((Number) accuracy.get("per_tag_accuracy_pct")).doubleValue();
        double parseP95 = ((Number) regexParse.get("p95_ms")).doubleValue();
        double cleanP95 = ((Number) regexClean.get("p95_ms")).doubleValue();

        if (exactCaseAccuracy < minAccuracy) {
            reasons.add(String.format("exact-case accuracy %.6f%% < %.3f%%", exactCaseAccuracy, minAccuracy));
        }
        if (perTagAccuracy < minAccuracy) {
            reasons.add(String.format("per-tag accuracy %.6f%% < %.3f%%", perTagAccuracy, minAccuracy));
        }
        if (parseP95 >= maxP95Ms) {
            reasons.add(String.format("regex parse p95 %.6f ms >= %.6f ms", parseP95, maxP95Ms));
        }
        if (cleanP95 >= maxP95Ms) {
            reasons.add(String.format("regex clean p95 %.6f ms >= %.6f ms", cleanP95, maxP95Ms));
        }

        return new GateCheck(reasons.isEmpty(), reasons);
    }

    public static void writeReport(Path reportOutput, Path benchmarkOutput, Map<String, Object> benchmark, TestSummary tests,
            boolean specDictOk, boolean specCleanOk, GateCheck gates) throws IOException {
        Files.createDirectories(reportOutput.getParent());

        Map<String, Object> spec = asMap(benchmark.get("spec_sample"));
        Map<String, Object> accuracy = asMap(benchmark.get("accuracy"));

        StringBuilder out = new StringBuilder();
        out.append("# Java Lab Validation Report\n\n");
        out.append("- Generated (UTC): ").append(Instant.now()).append('\n');
        out.append(
                "- Method: deterministic JUnit + fuzz + spec reproduction + JMH-backed benchmark + gate checks\n\n");
        out.append("## Gate Status\n\n");
        out.append("- Unit tests: ").append(tests.pass ? "PASS" : "FAIL").append('\n');
        out.append("- Test count: ").append(tests.tests).append(" total, ").append(tests.failures).append(" failed\n");
        out.append("- Spec dictionary reproduction: ").append(specDictOk ? "PASS" : "FAIL").append('\n');
        out.append("- Spec clean-output reproduction: ").append(specCleanOk ? "PASS" : "FAIL").append('\n');
        out.append("- Accuracy/latency gates: ").append(gates.pass ? "PASS" : "FAIL").append("\n\n");

        out.append("## Spec Benchmark\n\n");
        out.append("- Input size: ").append(spec.get("input_chars")).append(" chars\n");
        out.append("- Tag count: ").append(spec.get("tag_count")).append('\n');
        out.append("- Regex parse avg: ").append(
                BenchmarkRunner.formatDouble(((Number) asMap(spec.get("regex_parse")).get("avg_ms")).doubleValue()))
                .append(" ms\n");
        out.append("- Regex parse p95: ").append(
                BenchmarkRunner.formatDouble(((Number) asMap(spec.get("regex_parse")).get("p95_ms")).doubleValue()))
                .append(" ms\n");
        out.append("- Regex clean avg: ").append(
                BenchmarkRunner.formatDouble(((Number) asMap(spec.get("regex_clean")).get("avg_ms")).doubleValue()))
                .append(" ms\n");
        out.append("- Regex clean p95: ").append(
                BenchmarkRunner.formatDouble(((Number) asMap(spec.get("regex_clean")).get("p95_ms")).doubleValue()))
                .append(" ms\n");
        out.append("- Regex total avg overhead: ").append(
                BenchmarkRunner.formatDouble(
                        ((Number) asMap(spec.get("regex_parse")).get("avg_ms")).doubleValue()
                                + ((Number) asMap(spec.get("regex_clean")).get("avg_ms")).doubleValue()))
                .append(" ms\n");
        out.append("- Linear parse avg: ").append(
                BenchmarkRunner.formatDouble(((Number) asMap(spec.get("linear_parse")).get("avg_ms")).doubleValue()))
                .append(" ms\n");
        out.append("- Linear clean avg: ").append(
                BenchmarkRunner.formatDouble(((Number) asMap(spec.get("linear_clean")).get("avg_ms")).doubleValue()))
                .append(" ms\n\n");

        out.append("## Accuracy Study\n\n");
        out.append("- Cases: ").append(accuracy.get("cases")).append('\n');
        out.append("- Total expected tags: ").append(accuracy.get("total_expected_tags")).append('\n');
        out.append("- Exact-case accuracy: ").append(
                BenchmarkRunner.formatDouble(((Number) accuracy.get("exact_case_accuracy_pct")).doubleValue()))
                .append("%\n");
        out.append("- Per-tag accuracy: ").append(
                BenchmarkRunner.formatDouble(((Number) accuracy.get("per_tag_accuracy_pct")).doubleValue()))
                .append("%\n\n");

        out.append("## Scaling Snapshot\n\n");
        List<Map<String, Object>> scaling = asListOfMap(benchmark.get("scaling"));
        for (Map<String, Object> row : scaling) {
            out.append("- ").append(row.get("chars")).append(" chars / ").append(row.get("tags"))
                    .append(" tags: parse avg ")
                    .append(BenchmarkRunner.formatDouble(((Number) asMap(row.get("parse")).get("avg_ms")).doubleValue()))
                    .append(" ms, clean avg ")
                    .append(BenchmarkRunner.formatDouble(((Number) asMap(row.get("clean")).get("avg_ms")).doubleValue()))
                    .append(" ms\n");
        }

        if (!gates.pass) {
            out.append("\n## Gate Fail Reasons\n\n");
            for (String reason : gates.reasons) {
                out.append("- ").append(reason).append('\n');
            }
        }

        out.append("\n## Artifacts\n\n");
        out.append("- Benchmark JSON: `").append(benchmarkOutput.toString()).append("`\n");
        out.append("- JMH raw JSON: `").append(asString(benchmark.get("jmh_raw_result_path"))).append("`\n");

        Files.writeString(reportOutput, out);
    }

    private static TestSummary readSurefireSummary(Path reportDir) {
        int tests = 0;
        int failures = 0;
        int errors = 0;
        int skipped = 0;
        try {
            if (!Files.exists(reportDir)) {
                return new TestSummary(false, 0, 0, 0, 0);
            }
            var factory = DocumentBuilderFactory.newInstance();
            var builder = factory.newDocumentBuilder();
            try (var stream = Files.list(reportDir)) {
                List<Path> files = stream.filter(p -> p.getFileName().toString().startsWith("TEST-")
                        && p.getFileName().toString().endsWith(".xml")).toList();
                for (Path file : files) {
                    Document doc = builder.parse(file.toFile());
                    NodeList suites = doc.getElementsByTagName("testsuite");
                    if (suites.getLength() > 0) {
                        Element suite = (Element) suites.item(0);
                        tests += Integer.parseInt(suite.getAttribute("tests"));
                        failures += Integer.parseInt(suite.getAttribute("failures"));
                        errors += Integer.parseInt(suite.getAttribute("errors"));
                        skipped += Integer.parseInt(suite.getAttribute("skipped"));
                    }
                }
            }
        } catch (Exception ex) {
            return new TestSummary(false, tests, failures + errors, errors, skipped);
        }
        return new TestSummary(failures == 0 && errors == 0 && tests > 0, tests, failures + errors, errors, skipped);
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> out = new LinkedHashMap<>();
        for (int i = 0; i < args.length - 1; i += 2) {
            out.put(args[i], args[i + 1]);
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object value) {
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> asListOfMap(Object value) {
        return (List<Map<String, Object>>) value;
    }

    private static String asString(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    public record GateCheck(boolean pass, List<String> reasons) {
    }

    public record TestSummary(boolean pass, int tests, int failures, int errors, int skipped) {
    }
}

