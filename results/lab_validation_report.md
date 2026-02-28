# Consolidated Lab Validation Report

- Generated (UTC): 2026-02-28T20:52:57.423629+00:00
- Scope: Python parser/cleaner, TypeScript port, Java port, Python TMS core, ThoughtGraph, Reflection Engine, and Phase 4 multi-model/agentic loop integrations

## Gate Status

- Python tests: PASS
- Python parser gates (accuracy>=99.9, p95<1ms): PASS
- TMS quality gate (top1>=99%): PASS
- Reflection gate (success>=99%, p95<50ms): PASS
- Phase 4 agentic gate (store/reflection/recall>=99%, p95<120ms): PASS
- TypeScript artifacts present: YES
- Java artifacts present: YES

## Python Wrapper

- Regex parse avg: 0.010797 ms
- Regex parse p95: 0.014700 ms
- Regex clean avg: 0.011721 ms
- Regex clean p95: 0.019800 ms
- Exact-case accuracy: 100.00%
- Per-tag accuracy: 100.00%

## TypeScript Wrapper

- Regex parse avg: 0.001512 ms
- Regex parse p95: 0.001708 ms
- Regex clean avg: 0.001782 ms
- Regex clean p95: 0.002413 ms
- Exact-case accuracy: 100.00%
- Per-tag accuracy: 100.00%

## Java Wrapper

- Regex parse avg: 0.013928 ms
- Regex parse p95: 0.016300 ms
- Regex clean avg: 0.011700 ms
- Regex clean p95: 0.018000 ms
- Exact-case accuracy: 100.00%
- Per-tag accuracy: 100.00%

## TMS Core (Python)

- Vector backend: numpy
- Store single avg: 6.406191 ms
- Batch store (20) avg: 19.373200 ms
- Retrieve filtered avg: 7.496725 ms
- Semantic search avg: 18.882689 ms
- Semantic search p95: 23.242400 ms
- Top-1 exact match: 100.00%

## TMS Graph + Reflection (Python)

- Graph backend: networkx
- Add thought avg: 47.285770 ms
- Link avg: 3.867564 ms
- Find paths avg: 1.796947 ms
- Cluster avg: 3.918017 ms
- Reflection latency avg: 13.902678 ms
- Reflection latency p95: 24.580000 ms
- Reflection success rate: 100.00%

## Phase 4 Agentic Loop (Python)

- Turn total avg: 55.574818 ms
- Turn total p95: 89.497400 ms
- Completion avg: 38.226741 ms
- Reflection p95: 93.593700 ms
- Thought store success rate: 100.00%
- Reflection success rate: 100.00%
- Recall probe hit rate: 100.00%

## Artifacts

- Python benchmark: `results/benchmark_results.json`
- TMS benchmark: `results/tms_benchmark_results.json`
- TMS graph benchmark: `results/tms_graph_benchmark_results.json`
- Agent loop benchmark: `results/agent_loop_benchmark_results.json`
- TypeScript benchmark: `typescript/results/benchmark_results.json`
- Java benchmark: `java/results/benchmark_results.json`

## Python Test Output

```text
(no stdout)
test_async_run (test_agent_loop.TestAgentLoop.test_async_run) ... ok
test_run_session (test_agent_loop.TestAgentLoop.test_run_session) ... ok
test_run_turn_reflection_frequency (test_agent_loop.TestAgentLoop.test_run_turn_reflection_frequency) ... ok
test_clean_removes_tags_and_normalizes_whitespace (test_core.TestThoughtWrapperCore.test_clean_removes_tags_and_normalizes_whitespace) ... ok
test_invalid_tag_name_raises (test_core.TestThoughtWrapperCore.test_invalid_tag_name_raises) ... ok
test_linear_cleaner_removes_nested_tag (test_core.TestThoughtWrapperCore.test_linear_cleaner_removes_nested_tag) ... ok
test_linear_parser_handles_nested_brackets (test_core.TestThoughtWrapperCore.test_linear_parser_handles_nested_brackets) ... ok
test_no_tags_returns_empty_map (test_core.TestThoughtWrapperCore.test_no_tags_returns_empty_map) ... ok
test_parse_and_clean_convenience (test_core.TestThoughtWrapperCore.test_parse_and_clean_convenience) ... ok
test_parse_extracts_multiple_tags (test_core.TestThoughtWrapperCore.test_parse_extracts_multiple_tags) ... ok
test_parse_handles_multiline_content (test_core.TestThoughtWrapperCore.test_parse_handles_multiline_content) ... ok
test_parse_with_custom_tag_name (test_core.TestThoughtWrapperCore.test_parse_with_custom_tag_name) ... ok
test_unclosed_tag_is_ignored (test_core.TestThoughtWrapperCore.test_unclosed_tag_is_ignored) ... ok
test_clean_output_has_no_tag_markers (test_fuzz.TestFuzz.test_clean_output_has_no_tag_markers) ... ok
test_randomized_extraction_accuracy (test_fuzz.TestFuzz.test_randomized_extraction_accuracy) ... ok
test_randomized_thought_ingestion (test_phase4_fuzz.TestPhase4Fuzz.test_randomized_thought_ingestion) ... ok
test_thoughtwrapper_core_alias (test_public_namespace.TestPublicNamespace.test_thoughtwrapper_core_alias) ... ok
test_thoughtwrapper_tms_alias (test_public_namespace.TestPublicNamespace.test_thoughtwrapper_tms_alias) ... ok
test_anthropic_client_success (test_sdk_clients.TestSdkClients.test_anthropic_client_success) ... ok
test_llamacpp_client_success (test_sdk_clients.TestSdkClients.test_llamacpp_client_success) ... ok
test_ollama_client_success (test_sdk_clients.TestSdkClients.test_ollama_client_success) ... ok
test_openai_client_missing_key (test_sdk_clients.TestSdkClients.test_openai_client_missing_key) ... ok
test_openai_client_success (test_sdk_clients.TestSdkClients.test_openai_client_success) ... ok
test_xai_client_success (test_sdk_clients.TestSdkClients.test_xai_client_success) ... ok
test_async_complete (test_sdk_thought_llm.TestSdkThoughtLLM.test_async_complete) ... ok
test_complete_slash_enforcement_with_linear_fallback (test_sdk_thought_llm.TestSdkThoughtLLM.test_complete_slash_enforcement_with_linear_fallback) ... ok
test_complete_xml_ingestion_and_cleaning (test_sdk_thought_llm.TestSdkThoughtLLM.test_complete_xml_ingestion_and_cleaning) ... ok
test_cross_session_recall_via_parent_lineage (test_sdk_thought_llm.TestSdkThoughtLLM.test_cross_session_recall_via_parent_lineage) ... ok
test_reflection_frequency_behavior (test_sdk_thought_llm.TestSdkThoughtLLM.test_reflection_frequency_behavior) ... ok
test_exact_clean_output_reproduction (test_spec_reproduction.TestSpecReproduction.test_exact_clean_output_reproduction) ... ok
test_exact_hash_map_reproduction (test_spec_reproduction.TestSpecReproduction.test_exact_hash_map_reproduction) ... ok
test_latency_is_sub_millisecond_class (test_spec_reproduction.TestSpecReproduction.test_latency_is_sub_millisecond_class) ... ok
test_import_jsonl (test_thought_cli.TestThoughtCli.test_import_jsonl) ... ok
test_loop_and_reflect_commands (test_thought_cli.TestThoughtCli.test_loop_and_reflect_commands) ... ok
test_store_and_retrieve (test_thought_cli.TestThoughtCli.test_store_and_retrieve) ... ok
test_store_requires_input (test_thought_cli.TestThoughtCli.test_store_requires_input) ... ok
test_async_methods (test_tms_core.TestTmsCore.test_async_methods) ... ok
test_batch_store_is_atomic_on_error (test_tms_core.TestTmsCore.test_batch_store_is_atomic_on_error) ... ok
test_parse_and_store_pipeline_linear_fallback (test_tms_core.TestTmsCore.test_parse_and_store_pipeline_linear_fallback) ... ok
test_parse_and_store_pipeline_regex (test_tms_core.TestTmsCore.test_parse_and_store_pipeline_regex) ... ok
test_retrieve_with_filters (test_tms_core.TestTmsCore.test_retrieve_with_filters) ... ok
test_semantic_search_ranking (test_tms_core.TestTmsCore.test_semantic_search_ranking) ... ok
test_store_and_retrieve_roundtrip (test_tms_core.TestTmsCore.test_store_and_retrieve_roundtrip) ... ok
test_thought_model_validates_confidence (test_tms_core.TestTmsCore.test_thought_model_validates_confidence) ... ok
test_randomized_parse_and_store_counts (test_tms_fuzz.TestTmsFuzz.test_randomized_parse_and_store_counts) ... ok
test_randomized_store_retrieve_integrity (test_tms_fuzz.TestTmsFuzz.test_randomized_store_retrieve_integrity) ... ok
test_add_and_temporal_link (test_tms_graph.TestTmsGraph.test_add_and_temporal_link) ... ok
test_async_graph_methods (test_tms_graph.TestTmsGraph.test_async_graph_methods) ... ok
test_cluster_by_topic (test_tms_graph.TestTmsGraph.test_cluster_by_topic) ... ok
test_cross_session_recall_with_graph_expansion (test_tms_graph.TestTmsGraph.test_cross_session_recall_with_graph_expansion) ... ok
test_link_and_find_paths (test_tms_graph.TestTmsGraph.test_link_and_find_paths) ... ok
test_temporal_range (test_tms_graph.TestTmsGraph.test_temporal_range) ... ok
test_random_graph_operations_stability (test_tms_graph_fuzz.TestTmsGraphFuzz.test_random_graph_operations_stability) ... ok
test_random_reflection_cycles_stability (test_tms_graph_fuzz.TestTmsGraphFuzz.test_random_reflection_cycles_stability) ... ok
test_build_prompt (test_tms_prompt_helpers.TestTmsPromptHelpers.test_build_prompt) ... ok
test_system_prompts_include_tag_guidance (test_tms_prompt_helpers.TestTmsPromptHelpers.test_system_prompts_include_tag_guidance) ... ok
test_templates_exist (test_tms_prompt_helpers.TestTmsPromptHelpers.test_templates_exist) ... ok
test_async_reflect (test_tms_reflection.TestTmsReflection.test_async_reflect) ... ok
test_parse_structured_thoughts (test_tms_reflection.TestTmsReflection.test_parse_structured_thoughts) ... ok
test_reflect_default_cycle (test_tms_reflection.TestTmsReflection.test_reflect_default_cycle) ... ok
test_reflect_with_child_reflection_session (test_tms_reflection.TestTmsReflection.test_reflect_with_child_reflection_session) ... ok
test_reflect_with_custom_llm_callable (test_tms_reflection.TestTmsReflection.test_reflect_with_custom_llm_callable) ... ok

----------------------------------------------------------------------
Ran 62 tests in 3.372s

OK
```
