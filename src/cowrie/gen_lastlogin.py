"""Synthetic "Last login" line for honeyfs ``/etc/motd``."""

from __future__ import annotations

import random
from datetime import datetime, timedelta


def generate(ip: str = "0.0.0.0") -> str:
    """
    Return one line that resembles OpenSSH's last-login line.

    :param ip: Remote address shown in the line (e.g. attacker or a fake story IP).
    """
    minutes_ago = random.randint(5, 120)
    t = datetime.now() - timedelta(minutes=minutes_ago)
    return f"Last login: {t.strftime('%a %b %d %H:%M:%S %Y')} from {ip}"


def strip_leading_last_login_line(motd: bytes) -> bytes:
    """
    If *motd* begins with a ``Last login:`` line (e.g. from an old honeyfs file),
    remove it so we do not duplicate when the shell appends a fresh line after
    the banner body.
    """
    s = motd.lstrip()
    if not s.startswith(b"Last login:"):
        return motd
    rest = s.split(b"\n", 1)
    if len(rest) < 2:
        return b""
    return rest[1].lstrip()
