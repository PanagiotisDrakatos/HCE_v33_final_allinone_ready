# HCE Backtest & A/B — v3.3 (All‑in‑One)

**Ημερομηνία:** 2025-10-15

Περιλαμβάνει *όλα* σε ένα πακέτο:
- Shadow fill model (last/mark, bid/ask aware), slippage modes: fixed_ticks, bps, pct_spread, hybrid
- Order types: market, limit (queue/partials), stop, stop-limit
- Deterministic A/B (seed + stable event order)
- Repository abstraction (none|clickhouse|timescale) με batch writer, idempotent upserts, back-pressure
- Docker compose για ClickHouse / Timescale (με DDLs)
- Kahan summation στα reductions + UTC ISO normalizer
- JSON logs, metrics counters, tests (unit/golden + integration smoke)

## Quick start
```bash
pip install -r requirements.txt
# Optional: bring up DBs
docker compose up -d
# Run demo A/B
python backtest.py run --config examples/cfg.yaml --ab examples/A.json examples/B.json
# Run tests
pytest -q
```

## Resolve autofix conflicts during cherry-pick (WSL/Ubuntu)

Έτοιμο script για να λύνει conflicts από ruff/black autofix κατά το `git cherry-pick`, κρατώντας by default το "theirs" για αρχεία `.py` και config, και συνεχίζει αυτόματα το cherry-pick.

- Script: `scripts/resolve-autofix-conflicts.sh`
- Τρέχεις το παρακάτω μέσα από WSL/Ubuntu, από το root του repo:

```bash
# WSL path για το repo
cd /mnt/c/Users/User/Documents/GitHub/HCE_v33_final_allinone_ready

# αν δεν υπάρχει, φτιάξε τον φάκελο
mkdir -p scripts

# κάνε executable (μία φορά)
chmod +x scripts/resolve-autofix-conflicts.sh

# χρήση όταν κολλάει cherry-pick από autofix conflicts
scripts/resolve-autofix-conflicts.sh
```

Options:
- `--dry-run`    μόνο προεπισκόπηση (δεν αλλάζει τίποτα)
- `--verbose`    έξτρα logging
- `--keep-ours`  κράτα "ours" για business code, "theirs" για tests/configs

Παράδειγμα:
```bash
scripts/resolve-autofix-conflicts.sh --dry-run --verbose
scripts/resolve-autofix-conflicts.sh --keep-ours
```

Optional:
- Git alias
  ```bash
  git config --global alias.resolve-autofix '!bash scripts/resolve-autofix-conflicts.sh'
  # μετά: git resolve-autofix
  ```
- Μείωση conflicts
  ```bash
  git config --global rerere.enabled true
  git config --global core.autocrlf input
  # .gitattributes έχει ήδη: * text=auto eol=lf
  ```

## CI: Autofix (ruff/black)

Στο `.github/workflows/autofix.yml` υπάρχει workflow που τρέχει ruff/black:
- Σε pull requests: εκτελεί format, αλλά δεν κάνει push (ασφαλές για forks).
- Σε push προς `main`/`master`: αν βρει αλλαγές από format, τις κάνει commit & push αυτόματα.

Για να το απενεργοποιήσεις, σβήσε το αρχείο ή άλλαξε τα triggers στο `on:` section.
