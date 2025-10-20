# .prompts/BUGFIX.md — Minimal‑change bug fix

**Goal:** reproduce and fix with the smallest effective change.

## Steps
1) **REPRO** — precise steps, expected vs. actual.
2) **DIAGNOSE** — ranked hypotheses with evidence (files:lines).
3) **FIX** — apply minimal patch and explain why it’s sufficient.
4) **TESTS** — add/adjust tests that fail before and pass after.
5) **SANITY** — side effects, migrations, follow‑ups.
6) **VERIFY** — run {{test_command}} / {{lint_command}} / {{fmt_command}} / {{sec_command}} and summarize results.

## Output format
PLAN → EVIDENCE → PATCH (diffs) → TESTS → VERIFY → FOLLOW‑UPS.
