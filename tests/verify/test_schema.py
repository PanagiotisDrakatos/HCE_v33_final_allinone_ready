"""The published contract (verification/evidence.schema.json) and the in-code
validator must agree, so loosening the file cannot silently loosen the gate."""

import json
from pathlib import Path

import verify_core as core

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA = ROOT / "verification/evidence.schema.json"


def test_schema_file_exists():
    assert SCHEMA.is_file(), "the published evidence schema must exist"


def test_schema_required_covers_validator_keys():
    schema = json.loads(SCHEMA.read_text())
    required = set(schema.get("required", []))
    assert set(core._REQUIRED_KEYS) <= required, (
        f"schema required is missing: {set(core._REQUIRED_KEYS) - required}"
    )


def test_schema_names_required_check_ids():
    text = SCHEMA.read_text()
    for cid in core.REQUIRED_CHECK_IDS:
        assert cid in text, f"schema should document required check id {cid}"
