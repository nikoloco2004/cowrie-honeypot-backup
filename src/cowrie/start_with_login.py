"""
Write ``honeyfs/etc/motd`` (banner body only) and start Cowrie.

The SSH shell prints a synthetic ``Last login: … from <ip>`` **after** this
text (immediately above the prompt). The *from* address uses
:confval:`[honeypot] fake_addr` if set, else the real client. This file should
contain only the Debian/legal MOTD *body*.

**Edit the banner** by changing :data:`MOTD_BODY` below.

Run (venv active)::

    python -m cowrie.start_with_login
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Editable: post-login banner (MOTD body). A "Last login:" line is added by the shell.
# ---------------------------------------------------------------------------
MOTD_BODY = """The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
"""


def _project_root() -> Path:
    # src/cowrie/start_with_login.py -> repo root
    return Path(__file__).resolve().parent.parent.parent


def write_motd(motd_path: Path) -> None:
    """Write MOTD body to honeyfs; last-login is injected when the user connects."""
    motd_path.parent.mkdir(parents=True, exist_ok=True)
    motd_path.write_text(f"{MOTD_BODY.strip()}\n", encoding="utf-8")


def _start_cowrie(project_root: Path) -> int:
    os.chdir(project_root)
    cowrie = shutil.which("cowrie")
    if not cowrie:
        print(
            "cowrie: command not found. From the repository root: "
            "python3 -m venv cowrie-env && source cowrie-env/bin/activate && "
            "pip install -e .",
            file=sys.stderr,
        )
        return 1
    return subprocess.call([cowrie, "start"], cwd=project_root)


def main() -> int:
    root = _project_root()
    write_motd(root / "honeyfs" / "etc" / "motd")
    return _start_cowrie(root)


if __name__ == "__main__":
    raise SystemExit(main())
