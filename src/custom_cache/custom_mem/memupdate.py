"""Memory state update logic.

Reads state from memstate, applies plausible drift, writes back, and
flushes the formatted output to /proc/meminfo in Cowrie's honeyfs.

Revert to previous 2s throttle + fixed path behavior: in etc/cowrie.cfg set
    [meminfo]
    mode = legacy
  then restart Cowrie. Or: git log -p -- src/custom_cache/custom_mem/memupdate.py
"""

from __future__ import annotations

import os
import random
import time
from collections import OrderedDict
from os.path import abspath, dirname, join

from custom_mem import memstate

# ---------------------------------------------------------------------------
# Modes (see [meminfo] mode in etc/cowrie.cfg)
# ---------------------------------------------------------------------------
# legacy: 2.0s min interval between drifts, 0.3% max drift, optional old fallback path
# live:   ~0.12s min interval (repeated cat sees moving numbers), 0.4% drift, path from
#         [honeypot] contents_path (project root)
#
_DRIFT_FRACTION_LEGACY = 0.003
_DRIFT_FRACTION_LIVE = 0.004
_MIN_INTERVAL_LEGACY_SEC = 2.0
_MIN_INTERVAL_LIVE_SEC = 0.12

# If Cowrie config is unavailable, use this for honeyfs (developer layout).
_LEGACY_HONEYFS_FALLBACK = os.path.expanduser(
    "~/Documents/Emerge/cowrie-honeypot-backup/honeyfs/proc/meminfo"
)

# Cached path (must reset if cwd/config changes; Cowrie is one process, OK)
_honeyfs_path_cache: str | None = None
_last_config_mode: str | None = None


# ---------------------------------------------------------------------------
# Config + paths
# ---------------------------------------------------------------------------


def _project_root() -> str:
    """Project root: parent of `src/`, from cowrie package layout."""
    import cowrie.core.config as cc  # type: ignore[import-not-found]

    d = abspath(join(dirname(abspath(cc.__file__)), "..", "..", ".."))
    return d


def meminfo_mode() -> str:
    """Return 'live' or 'legacy' (default legacy if [meminfo] missing)."""
    try:
        from cowrie.core.config import CowrieConfig  # type: ignore[import-not-found]

        m = CowrieConfig.get("meminfo", "mode", fallback="legacy").strip().lower()
        if m in ("live", "legacy"):
            return m
    except Exception:
        pass
    return "legacy"


def _min_update_interval() -> float:
    return _MIN_INTERVAL_LIVE_SEC if meminfo_mode() == "live" else _MIN_INTERVAL_LEGACY_SEC


def _max_drift_fraction() -> float:
    return _DRIFT_FRACTION_LIVE if meminfo_mode() == "live" else _DRIFT_FRACTION_LEGACY


def honeyfs_meminfo_path() -> str:
    """
    On-disk file Cowrie's fs merges for /proc/meminfo.
    * live:    {project}/{[honeypot] contents_path}/proc/meminfo (portable, Pi-like)
    * legacy:  previous fixed expanduser path (full revert to old on-disk layout)
    """
    global _honeyfs_path_cache, _last_config_mode
    mode = meminfo_mode()
    if _honeyfs_path_cache is not None and _last_config_mode == mode:
        return _honeyfs_path_cache

    if mode == "live":
        try:
            from cowrie.core.config import CowrieConfig  # type: ignore[import-not-found]

            root = _project_root()
            sub = CowrieConfig.get("honeypot", "contents_path", fallback="honeyfs")
            path = abspath(join(root, sub, "proc", "meminfo"))
        except Exception:
            path = _LEGACY_HONEYFS_FALLBACK
    else:
        path = _LEGACY_HONEYFS_FALLBACK

    _honeyfs_path_cache = path
    _last_config_mode = mode
    return path


# Backward compatibility: importers and smoke tests
def __getattr__(name: str) -> str:  # PEP 562
    if name == "HONEYFS_MEMINFO":
        return honeyfs_meminfo_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

_last_update_ts = 0.0


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def _apply_drift(state, max_drift_fraction: float) -> OrderedDict:
    """Produce a new state with plausible correlated drift applied."""
    new = OrderedDict(state)
    total = new["MemTotal"]
    max_drift = int(total * max_drift_fraction)

    # Signed drift, biased toward memory being consumed.
    delta = random.randint(-max_drift // 2, max_drift)

    # 70/30 split: file cache vs anonymous pages.
    file_delta = int(delta * 0.7)
    anon_delta = delta - file_delta

    new["MemFree"] = _clamp(new["MemFree"] - delta, total // 20, total - 1000)

    new["Cached"] = max(0, new["Cached"] + file_delta)
    new["Active(file)"] = max(0, new["Active(file)"] + file_delta // 2)
    new["Inactive(file)"] = max(0, new["Inactive(file)"] + file_delta - file_delta // 2)
    new["AnonPages"] = max(0, new["AnonPages"] + anon_delta)
    new["Active(anon)"] = max(0, new["Active(anon)"] + anon_delta)

    new["Active"] = new["Active(anon)"] + new["Active(file)"]
    new["Inactive"] = new["Inactive(anon)"] + new["Inactive(file)"]

    reclaim = new["Cached"] + new["SReclaimable"] + new["Buffers"]
    new["MemAvailable"] = min(total, new["MemFree"] + reclaim - 64000)

    new["Buffers"] = _clamp(
        new["Buffers"] + random.randint(-500, 500), 10000, total // 20
    )
    new["Mapped"] = _clamp(
        new["Mapped"] + random.randint(-200, 200), 10000, total // 4
    )
    new["Dirty"] = _clamp(new["Dirty"] + random.randint(-20, 100), 0, 10000)

    return new


def _enforce_invariants(state):
    total = state["MemTotal"]
    assert state["MemFree"] >= 0, "MemFree < 0"
    assert state["MemFree"] <= total, "MemFree > MemTotal"
    assert state["MemAvailable"] >= state["MemFree"], "MemAvailable < MemFree"
    assert state["MemAvailable"] <= total, "MemAvailable > MemTotal"
    assert state["SwapFree"] <= state["SwapTotal"], "SwapFree > SwapTotal"
    assert state["Active"] == state["Active(anon)"] + state["Active(file)"], (
        "Active != Active(anon) + Active(file)"
    )
    assert state["Inactive"] == state["Inactive(anon)"] + state["Inactive(file)"], (
        "Inactive != Inactive(anon) + Inactive(file)"
    )


def _format_meminfo(state):
    """Format as /proc/meminfo text. Kernel format: '%-16s%8lu kB\\n'."""
    lines = []
    for key, val in state.items():
        label = f"{key}:"
        lines.append(f"{label:<16}{val:>8} kB")
    return "\n".join(lines) + "\n"


def _flush_to_honeyfs(state):
    """Atomically write formatted meminfo to the attacker-visible path."""
    mpath = honeyfs_meminfo_path()
    text = _format_meminfo(state)
    tmp = mpath + ".tmp"
    try:
        os.makedirs(os.path.dirname(mpath), exist_ok=True)
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, mpath)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def update():
    """Advance state by one drift step if throttle allows. Flushes to honeyfs.
    Call at the start of any command handler that reports memory."""
    global _last_update_ts
    min_iv = _min_update_interval()
    now = time.time()
    if now - _last_update_ts < min_iv:
        return

    frac = _max_drift_fraction()
    current = memstate.get_state()
    new = _apply_drift(current, frac)

    try:
        _enforce_invariants(new)
    except AssertionError:
        return

    memstate.set_state(new)
    _flush_to_honeyfs(new)
    _last_update_ts = now


def force_update():
    """Apply drift unconditionally (ignores throttle)."""
    global _last_update_ts
    _last_update_ts = 0.0
    update()


def read_fresh_honeyfs_bytes(virtual: str) -> bytes | None:
    """
    Read the on-disk file Cowrie *should* show for a dynamic path, bypassing
    the virtual fs pickle (which may cache A_CONTENTS and ignore honeyfs
    rewrites). Call after update().
    """
    if virtual != "/proc/meminfo":
        return None
    p = honeyfs_meminfo_path()
    try:
        if os.path.isfile(p):
            with open(p, "rb") as f:
                return f.read()
    except OSError:
        pass
    return None


def bootstrap_honeyfs():
    """Ensure honeyfs/proc/meminfo exists and reflects current state without
    advancing drift. Call at Cowrie startup."""
    current = memstate.get_state()
    _flush_to_honeyfs(current)
