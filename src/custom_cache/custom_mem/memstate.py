"""Memory state for the honeypot.

SINGLE SOURCE OF TRUTH for memory values exposed by /proc/meminfo, free,
vmstat, top, and related commands. Holds current state and provides
read/write primitives. Contains NO update logic — see memupdate.py.

All values in kB. Field order matches ground truth /proc/meminfo exactly.
"""

import json
import os
import threading
from collections import OrderedDict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Persistent state cache (internal — attacker never sees this file).
STATE_FILE = os.path.expanduser("~/Documents/Emerge/cowrie-honeypot-backup/var/memstate.json")


# ---------------------------------------------------------------------------
# Baseline — captured from ground truth Pi.
# Field order is SIGNIFICANT. Do not reorder.
# ---------------------------------------------------------------------------

_BASELINE = OrderedDict([
    ("MemTotal",       16608192),
    ("MemFree",        13976112),
    ("MemAvailable",   15056880),
    ("Buffers",          133328),
    ("Cached",           880304),
    ("SwapCached",            0),
    ("Active",          1414064),
    ("Inactive",         775568),
    ("Active(anon)",    1189136),
    ("Inactive(anon)",        0),
    ("Active(file)",     224928),
    ("Inactive(file)",   775568),
    ("Unevictable",           0),
    ("Mlocked",               0),
    ("SwapTotal",       2097136),
    ("SwapFree",        2097136),
    ("Zswap",                 0),
    ("Zswapped",              0),
    ("Dirty",                48),
    ("Writeback",             0),
    ("AnonPages",       1176896),
    ("Mapped",           101840),
    ("Shmem",             13584),
    ("KReclaimable",     203488),
    ("Slab",             256528),
    ("SReclaimable",     203488),
    ("SUnreclaim",        53040),
    ("KernelStack",        5296),
    ("PageTables",        73392),
    ("SecPageTables",       128),
    ("NFS_Unstable",          0),
    ("Bounce",                0),
    ("WritebackTmp",          0),
    ("CommitLimit",    10401232),
    ("Committed_AS",    1457056),
    ("VmallocTotal",  68447887360),
    ("VmallocUsed",       68784),
    ("VmallocChunk",          0),
    ("Percpu",             1344),
    ("CmaTotal",          65536),
    ("CmaFree",           55296),
])


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()
_cache = None


def _load_from_disk():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f, object_pairs_hook=OrderedDict)
        if list(data.keys()) != list(_BASELINE.keys()):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _save_to_disk(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, STATE_FILE)
    except OSError:
        pass


def _init_state():
    global _cache
    loaded = _load_from_disk()
    if loaded is not None:
        _cache = loaded
    else:
        _cache = OrderedDict(_BASELINE)
        _save_to_disk(_cache)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_state():
    """Return a COPY of the current state. Mutations don't affect canonical."""
    with _LOCK:
        if _cache is None:
            _init_state()
        return OrderedDict(_cache)


def set_state(new_state):
    """Replace current state. Keys and order must match baseline."""
    with _LOCK:
        if list(new_state.keys()) != list(_BASELINE.keys()):
            raise ValueError(
                "set_state: keys or order do not match baseline. "
                "Field order is load-bearing — do not reorder."
            )
        global _cache
        _cache = OrderedDict(new_state)
        _save_to_disk(_cache)


def get_field(name):
    return get_state()[name]


def reset_to_baseline():
    with _LOCK:
        global _cache
        _cache = OrderedDict(_BASELINE)
        _save_to_disk(_cache)


def get_baseline():
    return OrderedDict(_BASELINE)


def field_order():
    return list(_BASELINE.keys())