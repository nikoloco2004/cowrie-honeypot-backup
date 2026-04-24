"""Memory state update logic.

Reads state from memstate, applies plausible drift, writes back, and
flushes the formatted output to /proc/meminfo in Cowrie's honeyfs.
"""

import os
import random
import time
from collections import OrderedDict

from custom_mem import memstate


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HONEYFS_MEMINFO = os.path.expanduser("~/Documents/Emerge/cowrie-honeypot-backup/honeyfs/proc/meminfo")

# Rapid back-to-back reads see the same snapshot (idle system).
_MIN_UPDATE_INTERVAL_SEC = 2.0

# Max per-update drift: 0.3% of MemTotal.
_MAX_DRIFT_FRACTION = 0.003


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

_last_update_ts = 0.0


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def _apply_drift(state):
    """Produce a new state with plausible correlated drift applied."""
    new = OrderedDict(state)
    total = new["MemTotal"]
    max_drift = int(total * _MAX_DRIFT_FRACTION)

    # Signed drift, biased toward memory being consumed.
    delta = random.randint(-max_drift // 2, max_drift)

    # 70/30 split: file cache vs anonymous pages.
    file_delta = int(delta * 0.7)
    anon_delta = delta - file_delta

    new["MemFree"] = _clamp(new["MemFree"] - delta, total // 20, total - 1000)

    new["Cached"]         = max(0, new["Cached"]         + file_delta)
    new["Active(file)"]   = max(0, new["Active(file)"]   + file_delta // 2)
    new["Inactive(file)"] = max(0, new["Inactive(file)"] + file_delta - file_delta // 2)
    new["AnonPages"]      = max(0, new["AnonPages"]      + anon_delta)
    new["Active(anon)"]   = max(0, new["Active(anon)"]   + anon_delta)

    new["Active"]   = new["Active(anon)"]   + new["Active(file)"]
    new["Inactive"] = new["Inactive(anon)"] + new["Inactive(file)"]

    reclaim = new["Cached"] + new["SReclaimable"] + new["Buffers"]
    new["MemAvailable"] = min(total, new["MemFree"] + reclaim - 64000)

    new["Buffers"] = _clamp(new["Buffers"] + random.randint(-500, 500),
                            10000, total // 20)
    new["Mapped"]  = _clamp(new["Mapped"]  + random.randint(-200, 200),
                            10000, total // 4)
    new["Dirty"]   = _clamp(new["Dirty"]   + random.randint(-20, 100),
                            0, 10000)

    return new


def _enforce_invariants(state):
    total = state["MemTotal"]
    assert state["MemFree"] >= 0, "MemFree < 0"
    assert state["MemFree"] <= total, "MemFree > MemTotal"
    assert state["MemAvailable"] >= state["MemFree"], "MemAvailable < MemFree"
    assert state["MemAvailable"] <= total, "MemAvailable > MemTotal"
    assert state["SwapFree"] <= state["SwapTotal"], "SwapFree > SwapTotal"
    assert state["Active"] == state["Active(anon)"] + state["Active(file)"], \
        "Active != Active(anon) + Active(file)"
    assert state["Inactive"] == state["Inactive(anon)"] + state["Inactive(file)"], \
        "Inactive != Inactive(anon) + Inactive(file)"


def _format_meminfo(state):
    """Format as /proc/meminfo text. Kernel format: '%-16s%8lu kB\\n'."""
    lines = []
    for key, val in state.items():
        label = f"{key}:"
        lines.append(f"{label:<16}{val:>8} kB")
    return "\n".join(lines) + "\n"


def _flush_to_honeyfs(state):
    """Atomically write formatted meminfo to the attacker-visible path."""
    text = _format_meminfo(state)
    tmp = HONEYFS_MEMINFO + ".tmp"
    try:
        os.makedirs(os.path.dirname(HONEYFS_MEMINFO), exist_ok=True)
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, HONEYFS_MEMINFO)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def update():
    """Advance state by one drift step if throttle allows. Flushes to honeyfs.
    Call at the start of any command handler that reports memory."""
    global _last_update_ts
    now = time.time()
    if now - _last_update_ts < _MIN_UPDATE_INTERVAL_SEC:
        return

    current = memstate.get_state()
    new = _apply_drift(current)

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


def bootstrap_honeyfs():
    """Ensure honeyfs/proc/meminfo exists and reflects current state without
    advancing drift. Call at Cowrie startup."""
    current = memstate.get_state()
    _flush_to_honeyfs(current)