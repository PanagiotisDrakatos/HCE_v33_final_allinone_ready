"""Structural policy for CI, the compose overlay, the security config, and the
test markers. Every assertion here is red on origin/main and green once the
verify-plane change lands.
"""

from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
LANES = {"static", "unit", "pr-policy", "security", "runtime-verify"}


class _ComposeLoader(yaml.SafeLoader):
    """SafeLoader that tolerates Compose merge tags (!override, !reset)."""


def _compose_tag(loader, suffix, node):
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return loader.construct_scalar(node)


_ComposeLoader.add_multi_constructor("!", _compose_tag)


def _yaml(rel):
    return yaml.load((ROOT / rel).read_text(), Loader=_ComposeLoader)


def test_ci_has_five_lanes_and_aggregate():
    ci = _yaml(".github/workflows/ci.yml")
    jobs = set(ci["jobs"])
    assert LANES <= jobs, f"missing lanes: {LANES - jobs}"
    assert "aggregate" in jobs
    agg = ci["jobs"]["aggregate"]
    assert set(agg["needs"]) == LANES, agg.get("needs")
    # aggregate must run even when a lane fails, then check each result.
    assert str(agg.get("if")).strip() in ("always()", "${{ always() }}")
    assert "name" not in agg, "aggregate must keep its job id as the check-run name"


def test_no_continue_on_error_anywhere():
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "continue-on-error" not in text


def test_ci_does_not_override_cov_scope():
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "--cov=." not in text, "let pytest.ini own the coverage scope"


def test_placeholder_backtests_job_gone():
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "Backtests would run here" not in text


def test_actions_are_sha_pinned():
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    uses = re.findall(r"uses:\s*([^\s]+)", text)
    third_party = [u for u in uses if "/" in u and not u.startswith("./")]
    bad = [u for u in third_party if not re.search(r"@[0-9a-f]{40}$", u)]
    assert not bad, f"unpinned actions: {bad}"


def test_compose_overlay_is_parallel_safe_and_healthchecked():
    overlay = _yaml("compose.verify.yml")
    ts = overlay["services"]["timescaledb"]
    assert "healthcheck" in ts, "overlay must add a healthcheck"
    assert "container_name" not in ts, "fixed container_name breaks parallel runs"
    ports = ts.get("ports", [])
    for p in ports:
        # ephemeral host port only: no bare "5432:5432"
        assert re.match(r"^127\.0\.0\.1::\d+$", str(p)) or "::" in str(p), p


def test_base_compose_pins_timescale_by_digest():
    base = _yaml("docker-compose.yml")
    img = base["services"]["timescaledb"]["image"]
    assert "pg16-latest" not in img, "floating tag is not reproducible"
    assert "@sha256:" in img, f"pin by digest: {img}"


def test_security_command_is_blocking():
    proj = (ROOT / ".prompts/_project.yaml").read_text()
    for line in proj.splitlines():
        if line.strip().startswith("sec:") and "bandit" in line:
            assert "|| true" not in line, line


def test_integration_tests_are_marked_and_real():
    itest = (ROOT / "tests/integration/test_persistence.py").read_text()
    assert "pytest.mark.integration" in itest, "real integration tests must be marked"
    for rel in ("tests/integration/test_roundtrip_timescale.py",):
        body = (ROOT / rel).read_text()
        assert "assert True" not in body, f"{rel} is still a placeholder"


def test_verify_dir_is_never_tracked():
    import subprocess

    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", ".verify"], capture_output=True, text=True, check=True
    )
    assert not out.stdout.strip(), ".verify/ must be gitignored, never committed"
