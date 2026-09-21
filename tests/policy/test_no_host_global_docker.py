"""Reject host-global Docker destruction anywhere an ordinary developer, CI, or
agent command can reach it.

This is a regression guard against reintroducing something like the removed
`make deep-reset`, not an adversarial security boundary: a determined committer
can defeat any lexical scanner (base64, `eval`, variable indirection). It closes
the realistic accidental-reintroduction forms and the file-scope holes; the
adversarial evasions are enumerated below with must_flag=False as a stated
ceiling. Violation strings are built by concatenation so this file is never
flagged by its own live scan, and tests/** is excluded structurally.
"""

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent.parent

# Files whose contents are executable text an agent/CI/dev can run. Both bare and
# `**/`-prefixed forms because git pathspec globs do not cross `/` on their own.
SCOPE_GLOBS = (
    "Makefile",
    "**/Makefile",
    "makefile",
    "**/makefile",
    "*.mk",
    "**/*.mk",
    "justfile",
    "Justfile",
    "**/justfile",
    "**/Justfile",
    "*.sh",
    "**/*.sh",
    "scripts/**",
    ".scripts/**",
    "hooks/**",
    ".github/**",
    ".prompts/**",
    "Dockerfile",
    "Dockerfile*",
    "**/Dockerfile",
    "**/Dockerfile*",
    "install_hooks.sh",
    "compose*.yml",
    "compose*.yaml",
    "**/compose*.yml",
    "**/compose*.yaml",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "**/docker-compose*.yml",
    "**/docker-compose*.yaml",
)
# tests/** is never scanned (it would flag its own fixtures).
EXCLUDE = (":(exclude)tests/**",)

# R1: any host prune (system/volume/network/builder/container prune).
R1 = re.compile(r"\b(?:docker|podman|nerdctl)\b[^\n;|&]*\bprune\b")
# R2: bulk rm/rmi/stop/kill (incl. `container` long forms) fed by a command
# substitution, `$(...)` or backtick.
R2 = re.compile(
    r"\b(?:docker|podman)\s+(?:container\s+)?(?:rm|rmi|stop|kill)\b[^\n]*(?:\$\(|`)"
    r"|\b(?:docker|podman)\s+(?:volume|network)\s+rm\b[^\n]*(?:\$\(|`)"
)
# R3: a container listing piped into rm/stop/kill (xargs and friends, no `$(`).
R3 = re.compile(r"\b(?:docker|podman)\s+ps\b[^\n]*\|[^\n]*\b(?:rm|rmi|stop|kill)\b")


def _join_continuations(text):
    return text.replace("\\\n", " ")


def is_violation(line):
    line = _join_continuations(line)
    return bool(R1.search(line) or R2.search(line) or R3.search(line))


def _scoped_files():
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", *SCOPE_GLOBS, *EXCLUDE],
        capture_output=True,
        text=True,
        check=True,
    )
    seen, files = set(), []
    for p in out.stdout.split("\n"):
        if p.strip() and p not in seen:  # globs overlap; dedupe
            seen.add(p)
            files.append(ROOT / p)
    return files


# --- attack table: (label, line, must_flag) -------------------------------- #
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
    ("container rm long", f"{_D} container rm -f $({_D} ps -aq)", True),
    ("container stop long", f"{_D} container stop $({_D} ps -q)", True),
    ("backtick rm", f"{_D} rm -f `{_D} ps -aq`", True),
    ("xargs pipe rm", f"{_D} ps -aq | xargs -r {_D} rm -f", True),
    ("volume rm subst", f"{_D} volume rm $({_D} volume ls -q)", True),
    ("comment", f"# {_D} system prune", True),
    ("heredoc body", f"cat <<EOF\n{_D} system prune\nEOF", True),
    ("python subprocess", f'subprocess.run(["{_D}","system","prune"])', True),
    # allowed (project-scoped or named or non-destructive)
    ("scoped down", f"{_D} compose -p hce-verify-x down -v --remove-orphans", False),
    ("named rm", f"{_D} rm -f hce_timescale", False),
    ("build", f"{_D} build -t img .", False),
    # known ceiling: adversarial obfuscation a regression guard does not chase.
    ("ceiling: var indirection", f"d={_D}; $d system prune", False),
    ("ceiling: subshell semicolon", f"{_D} $(x=1; echo system) prune", False),
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
