# .prompts/REASONER_CRITIC.md — Private self‑critique (safe to use)

**Goal**: Improve correctness without exposing chain‑of‑thought.
**Method**:
- Think privately; **do not** reveal internal notes.
- Output only: a short **verdict** (correct / needs‑fix) + a **patch plan**.
- If needs‑fix: propose a concrete diff + new verification commands.
