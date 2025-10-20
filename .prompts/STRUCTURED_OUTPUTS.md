# .prompts/STRUCTURED_OUTPUTS.md — JSON‑Schema contract

**Why**: Deterministic downstream automation and CI gates.
**Rule**: Return JSON that **exactly** matches `SCHEMA_CONTRACT.json` (no extra keys).

**If the model cannot comply**: return a `validation_error` object with `reason` and `missing_fields`.
