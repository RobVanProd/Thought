package thoughtwrapper.bench;

import java.util.Map;
import java.util.concurrent.TimeUnit;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.State;

import thoughtwrapper.Samples;
import thoughtwrapper.ThoughtWrapper;

@State(Scope.Benchmark)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
public class ThoughtWrapperBenchmark {
    private final String spec = Samples.RAW_SPEC_OUTPUT;

    @Benchmark
    public Map<String, String> specRegexParse() {
        return ThoughtWrapper.parseThoughtTags(spec);
    }

    @Benchmark
    public String specRegexClean() {
        return ThoughtWrapper.cleanThoughtTags(spec);
    }

    @Benchmark
    public Map<String, String> specLinearParse() {
        return ThoughtWrapper.parseThoughtTagsLinear(spec);
    }

    @Benchmark
    public String specLinearClean() {
        return ThoughtWrapper.cleanThoughtTagsLinear(spec);
    }
}

