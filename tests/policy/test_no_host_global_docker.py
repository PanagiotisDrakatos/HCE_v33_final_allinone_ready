"""Reject host-global Docker destruction anywhere an ordinary developer, CI, or
agent command can reach it.

The scanner runs against the tracked tree (``git ls-files``) and against an
inline attack table. Violation strings in the table are built by concatenation
so this file is never flagged by its own live scan, and a guard row asserts
that ``tests/**`` is out of scope.
"""

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent.parent

# Files whose contents are executable text an agent/CI/dev can run.
SCOPE_GLOBS = (
    "Makefile",
    "makefile",
    "*.mk",
    "justfile",
    "Justfile",
    "scripts/**",
    ".scripts/**",
    "hooks/**",
    ".github/**",
    ".prompts/**",
    "install_hooks.sh",
    "compose*.yml",
    "docker-compose*.yml",
)

# R1: any prune of the host daemon. R2: bulk removal via a container-listing
# command substitution. Both span whitespace and simple substitutions.
R1 = re.compile(r"\b(?:docker|podman|nerdctl)\b[^\n;|&]*\bprune\b")
R2 = re.compile(
    r"\b(?:docker|podman)\s+(?:rm|rmi|stop|kill|container\s+prune|"
    r"volume\s+rm|network\s+rm)\b[^\n]*\$\("
)


def _join_continuations(text):
    return text.replace("\\\n", " ")


def is_violation(line):
    line = _join_continuations(line)
    return bool(R1.search(line) or R2.search(line))


def _scoped_files():
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", *SCOPE_GLOBS],
        capture_output=True,
        text=True,
        check=True,
    )
    return [ROOT / p for p in out.stdout.split("\n") if p.strip()]


# --- attack table: (label, line, must_flag) -------------------------------- #
# Strings are concatenated so this file is not flagged by the live scan below.
_D = "doc" + "ker"
ATTACK = [
    ("baseline prune", f"{_D} system prune -af --volumes || true", True),
    ("spacing/tab", f"{_D}   system\tprune", True),
    ("continuation", f"{_D} \\\n  system prune", True),
    ("cmd-subst verb", f"{_D} $(echo system) prune", True),
    ("sudo prefix", f"sudo {_D} system prune", True),
    ("env prefix", f"env DOCKER_HOST=x {_D} system prune", True),
    ("container prune", f"{_D} container prune -f", True),
    ("volume prune", f"{_D} volume prune", True),
    ("builder prune", f"{_D} builder prune", True),
    ("rm all", f"{_D} rm -f $({_D} ps -aq)", True),
    ("stop all", f"{_D} stop $({_D} ps -q)", True),
    ("comment", f"# {_D} system prune", True),
    ("heredoc body", f"cat <<EOF\n{_D} system prune\nEOF", True),
    ("python subprocess", f'subprocess.run(["{_D}","system","prune"])', True),
    ("scoped down", f"{_D} compose -p hce-verify-x down -v --remove-orphans", False),
    ("named rm", f"{_D} rm -f hce_timescale", False),
    ("build", f"{_D} build -t img .", False),
]


def test_attack_table_each_row():
    for label, line, must_flag in ATTACK:
        assert is_violation(line) is must_flag, f"{label!r}: {line!r}"


def test_live_tree_is_clean():
    hits = []
    for f in _scoped_files():
        try:
            text = f.read_text(errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(_join_continuations(text).splitlines(), 1):
            if is_violation(line):
                hits.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not hits, "host-global docker in tracked tree:\n" + "\n".join(hits)


def test_this_test_is_out_of_scope():
    # The scanner must never read tests/**, or it would flag its own fixtures.
    for f in _scoped_files():
        assert "tests/" not in str(f.relative_to(ROOT)), f
