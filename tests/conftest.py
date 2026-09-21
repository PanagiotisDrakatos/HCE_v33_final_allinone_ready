"""Make the verification kernel importable from tests.

`scripts/` is not a package; the kernel is loaded by putting it on sys.path so
`import verify` and `import verify_core` resolve for the tests under
`tests/verify/`. Harmless to every other test.
"""

from pathlib import Path
import sys

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
