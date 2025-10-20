# .prompts/MULTIAGENT_PLAYBOOK.md — Orchestrated pipeline (Spec → Implement → Verify → Gate)

**Roles & Handoffs**
1) **ARCHITECT** → writes/updates an ADR, interfaces, NFRs.
2) **IMPLEMENTER** → minimal diffs + tests.
3) **REVIEWER** → principled code review.
4) **QA** → deterministic unit/integration/E2E; fail‑first regressions.
5) **SECURITY** → CodeQL/dep scan/SBOM/license notes.
6) **SRE** → SLO/error‑budget check; release gate.
7) **RELEASE** → changelog, version, rollout plan.

**Contract JSON** — every role MUST output this schema (see `SCHEMA_CONTRACT.json`).

**Loop**
- Clarify (≤3 Qs) → Plan (bullets) → Patch (diffs) → Verify (commands) → Gate (risk notes + commit).
