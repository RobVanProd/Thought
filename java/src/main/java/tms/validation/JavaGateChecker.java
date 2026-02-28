package tms.validation;

import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import thoughtwrapper.validation.LabValidate;
import thoughtwrapper.validation.LabValidate.GateCheck;

public final class JavaGateChecker {
    private static final ObjectMapper JSON = new ObjectMapper();

    private JavaGateChecker() {
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> parsed = parseArgs(args);
        Path input = Path.of(parsed.getOrDefault("--input", "results/benchmark_results.json"));
        double minAccuracy = Double.parseDouble(parsed.getOrDefault("--min-accuracy", "99.9"));
        double maxP95 = Double.parseDouble(parsed.getOrDefault("--max-p95-ms", "1.0"));

        Map<String, Object> benchmark = JSON.readValue(input.toFile(), new TypeReference<>() {
        });
        GateCheck check = LabValidate.evaluateGates(benchmark, minAccuracy, maxP95);

        if (!check.pass()) {
            System.err.println("CI gates: FAIL");
            for (String reason : check.reasons()) {
                System.err.println("- " + reason);
            }
            System.exit(1);
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> accuracy = (Map<String, Object>) benchmark.get("accuracy");
        @SuppressWarnings("unchecked")
        Map<String, Object> spec = (Map<String, Object>) benchmark.get("spec_sample");
        @SuppressWarnings("unchecked")
        Map<String, Object> parse = (Map<String, Object>) spec.get("regex_parse");
        @SuppressWarnings("unchecked")
        Map<String, Object> clean = (Map<String, Object>) spec.get("regex_clean");

        System.out.println("CI gates: PASS");
        System.out.printf("- exact-case accuracy: %.6f%%%n", ((Number) accuracy.get("exact_case_accuracy_pct")).doubleValue());
        System.out.printf("- per-tag accuracy: %.6f%%%n", ((Number) accuracy.get("per_tag_accuracy_pct")).doubleValue());
        System.out.printf("- regex parse p95: %.6f ms%n", ((Number) parse.get("p95_ms")).doubleValue());
        System.out.printf("- regex clean p95: %.6f ms%n", ((Number) clean.get("p95_ms")).doubleValue());
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> out = new LinkedHashMap<>();
        for (int i = 0; i < args.length - 1; i += 2) {
            out.put(args[i], args[i + 1]);
        }
        return out;
    }
}

