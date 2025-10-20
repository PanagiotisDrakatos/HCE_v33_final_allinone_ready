# .prompts/REFACTOR.md — No‑behavior‑change refactor

**Objective:** <describe the refactor’s purpose>

## Rules
- Preserve public API and semantics; call out any incidental changes explicitly.
- Keep diffs small and focused (one concern per change).
- Improve readability, structure, and boundaries; avoid needless abstraction.

## Deliverables
- **RATIONALE** — debt removed; complexity/perf impact.
- **PATCH** — diffs; note moves/renames.
- **VERIFY** — run {{test_command}} / {{lint_command}} / {{fmt_command}}; include risk notes and rollback plan.
