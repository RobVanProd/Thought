# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Placeholder for upcoming Phase 5+ enhancements.

## [1.0.0] - 2026-02-28

### Added
- Phase 1 complete: parser/cleaner parity across Python, TypeScript, and Java with deterministic tests, fuzz tests, and benchmark gates.
- Phase 2 complete: Python Thought Memory System (TMS) core with typed thought schema, SQLite persistence, and hybrid semantic retrieval.
- Phase 3 complete: ThoughtGraph, cross-session recall, and reflection engine with validated quality/latency gates.
- Phase 4 complete: multi-model SDK bindings, agentic memory loop, CLI, FastAPI service template, and Docker deployment templates.
- Consolidated validation pipeline with one-command reproducibility via `scripts/lab_validate_all.py`.

### Changed
- Public Python namespace introduced as `thoughtwrapper` while preserving backward compatibility with `thought_wrapper`.
- Root documentation and release artifacts aligned for public release readiness.

### Validation
- Python tests: 62/62 PASS
- Parser accuracy: 100.00% exact-case and per-tag
- TMS top-1 semantic match: 100.00%
- Reflection success: 100.00%
- Recall hit rate: 100.00%
- All latency gates satisfied in consolidated report

[unreleased]: https://github.com/your-org/thoughtwrapper/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/thoughtwrapper/releases/tag/v1.0.0
