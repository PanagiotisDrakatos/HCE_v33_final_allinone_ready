# .prompts/TESTGEN.md — High‑value tests

**Strategy**
- Prefer fast, deterministic **unit tests**; add integration tests where they add clear value.
- Cover edge cases: empty/null/undefined, boundaries, timezones, unicode, streaming, slow I/O.
- For regressions: write the failing test first, then fix.

**Framework hints (match `_project.yaml`)**
- **Python** — pytest; use fixtures/parametrize.  Run with {{test_command}}.
- **TypeScript/JS** — use project’s configured runner (e.g., Vitest/Jest); run with {{test_command}}.
- **Go** — standard `testing`; use subtests/benchmarks/fuzzing as needed; run with {{test_command}}.
- **Rust** — `cargo test` for unit/integration/doc tests; run with {{test_command}}.
- **Java** — JUnit 5; run via Maven Surefire; run with {{test_command}}.

**Exit criteria**
- Tests fail before the fix and pass after.
- Suite passes under {{test_command}} locally and in CI.
