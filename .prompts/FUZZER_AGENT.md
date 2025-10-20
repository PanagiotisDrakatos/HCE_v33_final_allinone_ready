# .prompts/FUZZER_AGENT.md — Neg‑test & fuzz harness

**Scope**
- Generate property‑based tests and fuzz seeds for parsers, serializers, API boundaries.
- Include adversarial inputs: unicode, extreme sizes, timestamps, NaNs, injections.

**Output**
- Repro case → minimal fix → regression test. Note any DoS vectors found.
