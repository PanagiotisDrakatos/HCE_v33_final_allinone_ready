# .prompts/RAG_CODE_AGENT.md — Retrieval‑augmented engineering

**Policy**
- Prefer in‑repo sources and official docs.
- Cite exact versions/commit SHAs.
- Summarize; no long quotes.

**Flow**
1) Build short query → retrieve symbols/files.
2) Rank by semantic + static heuristics (owner, freshness, touched recently).
3) Synthesize minimal patch; include links/paths/lines inspected.
4) Validate via tests/lints/types.
