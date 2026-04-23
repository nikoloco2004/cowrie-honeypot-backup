# Copyright (c) 2026 Cowrie contributors
# Routines for optional Raspberry Pi 5 / Debian 13 "ground truth" shell output.
from __future__ import annotations

import importlib.resources
from importlib.abc import Traversable

from cowrie.core.config import CowrieConfig

_GROUND_ID = "pi5_debian13"
_PACKAGE = "cowrie.data"


def ground_truth_enabled() -> bool:
    return (
        CowrieConfig.get("shell", "ground_truth", fallback="none").lower()
        == _GROUND_ID
    )


def _resource_root() -> Traversable:
    return importlib.resources.files(_PACKAGE).joinpath("ground_truth", _GROUND_ID)


def load_ground_line(name: str) -> str:
    """
    Load a UTF-8 text blob from data/ground_truth/pi5_debian13/{name}
    and return a single string (may or may not end with newline).
    """
    p = _resource_root().joinpath(name)
    with p.open("r", encoding="utf-8", errors="replace") as f:
        return f.read()
