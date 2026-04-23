# Copyright (c) 2026 Cowrie contributors
# Single source of truth for process listings: parse ps_aux ground truth and
# derive ps -ef and top -bn1 so PIDs match across commands.
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass

from cowrie.core.config import CowrieConfig
from cowrie.core.ground_truth import load_ground_line
from cowrie.core import utils as cowrie_utils

_PS_AUX_DATA_RE = re.compile(
    r"^(\S+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)$"
)


@dataclass
class PsRow:
    user: str
    pid: int
    pcpu: str
    pmem: str
    vsz: int
    rss: int
    tty: str
    stat: str
    start: str
    time: str
    cmd: str


_rows_cache: list[PsRow] | None = None


def parse_ps_aux_text(text: str) -> list[PsRow]:
    rows: list[PsRow] = []
    for line in text.splitlines():
        line = line.rstrip("\n")
        if not line or line.startswith("USER "):
            continue
        m = _PS_AUX_DATA_RE.match(line)
        if not m:
            continue
        rows.append(
            PsRow(
                user=m.group(1),
                pid=int(m.group(2)),
                pcpu=m.group(3),
                pmem=m.group(4),
                vsz=int(m.group(5)),
                rss=int(m.group(6)),
                tty=m.group(7),
                stat=m.group(8),
                start=m.group(9),
                time=m.group(10),
                cmd=m.group(11).strip(),
            )
        )
    return rows


def get_ps_aux_rows() -> list[PsRow]:
    global _rows_cache
    if _rows_cache is None:
        _rows_cache = parse_ps_aux_text(load_ground_line("ps_aux.txt"))
    return _rows_cache


PS_AUX_HEADER = (
    "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
)


def format_ps_aux_line(r: PsRow) -> str:
    """procps-style columns matching Debian 13 reference captures."""
    vsz_s = f"{r.vsz:>7}"
    # 7-digit VSZ has no printf padding; a digit-ending %MEM would fuse (e.g. 0.5+5248640).
    if vsz_s[:1] != " ":
        mem_vsz = f"{r.pmem:>4} {vsz_s}"
    else:
        mem_vsz = f"{r.pmem:>4}{vsz_s}"
    return (
        f"{r.user:<8} {r.pid:>7} {r.pcpu:>4} {mem_vsz} {r.rss:>5} "
        f"{r.tty:<9}{r.stat:<5}{r.start:>5}{r.time:>7} {r.cmd}\n"
    )


def format_ps_aux_output(rows: list[PsRow]) -> str:
    return PS_AUX_HEADER + "".join(format_ps_aux_line(r) for r in rows)


def _row_is_captured_ps_listing(r: PsRow) -> bool:
    c = r.cmd.strip()
    if not c.startswith("ps"):
        return False
    tokens = c.split()
    if len(tokens) < 2:
        return False
    if "aux" in tokens:
        return True
    if "-ef" in tokens or ("-e" in tokens and "-f" in tokens):
        return True
    return False


def _row_is_session_shell(r: PsRow, tty: str) -> bool:
    if r.tty != tty:
        return False
    c = r.cmd.strip()
    if c in ("-bash", "bash", "/bin/bash", "/usr/bin/bash"):
        return True
    if c.startswith(("-bash ", "/bin/bash ", "/usr/bin/bash ")):
        return True
    return False


def _filtered_ps_aux_base(protocol) -> list[PsRow]:
    tty = protocol.get_ps_display_tty()
    return [
        r
        for r in get_ps_aux_rows()
        if not _row_is_captured_ps_listing(r) and not _row_is_session_shell(r, tty)
    ]


def _make_session_shell_row(protocol, utils_mod) -> PsRow:
    tpl = next(
        (
            r
            for r in get_ps_aux_rows()
            if r.cmd.strip() == "-bash" and r.tty.startswith("pts/")
        ),
        None,
    )
    vsz = tpl.vsz if tpl else 9008
    rss = tpl.rss if tpl else 5840
    stat = tpl.stat if tpl else "Ss+"
    tty = protocol.get_ps_display_tty()
    user = cowrie_utils.shell_visible_username(protocol)
    shell_pid = protocol.get_emulated_shell_pid()
    start = time.strftime("%H:%M", utils_mod.shell_clock_tuple_for(protocol.logintime))
    return PsRow(
        user=user,
        pid=shell_pid,
        pcpu="0.0",
        pmem="0.0",
        vsz=vsz,
        rss=rss,
        tty=tty,
        stat=stat,
        start=start,
        time="0:00",
        cmd="-bash",
    )


def _make_synthetic_ps_row(protocol, cmd: str, utils_mod) -> PsRow:
    pid = protocol.next_emulated_ps_pid()
    tty = protocol.get_ps_display_tty()
    user = cowrie_utils.shell_visible_username(protocol)
    start = time.strftime("%H:%M", utils_mod.shell_clock_tuple())
    tpl = next((r for r in get_ps_aux_rows() if r.cmd.strip() == "ps aux"), None)
    vsz = tpl.vsz if tpl else 9312
    rss = tpl.rss if tpl else 4080
    return PsRow(
        user=user,
        pid=pid,
        pcpu="0.0",
        pmem="0.0",
        vsz=vsz,
        rss=rss,
        tty=tty,
        stat="R+",
        start=start,
        time="0:00",
        cmd=cmd,
    )


def _aux_tail_noise(rows_so_far: list[PsRow], n: int) -> list[PsRow]:
    if n <= 0:
        return []
    templates = [r for r in get_ps_aux_rows() if "[kworker" in r.cmd]
    if not templates:
        templates = [r for r in get_ps_aux_rows() if r.user == "root" and r.cmd.startswith("[")]
    if not templates:
        return []
    from cowrie.core import utils

    start = time.strftime("%H:%M", utils.shell_clock_tuple())
    max_pid = max(r.pid for r in rows_so_far)
    out: list[PsRow] = []
    for _ in range(n):
        max_pid += random.randint(2, 40)
        t = random.choice(templates)
        out.append(
            PsRow(
                user=t.user,
                pid=max_pid,
                pcpu="0.0",
                pmem="0.0",
                vsz=0,
                rss=0,
                tty="?",
                stat="I",
                start=start,
                time="0:00",
                cmd=t.cmd,
            )
        )
    return out


def build_session_ps_rows(
    protocol,
    *,
    purpose: str,
    ps_display_cmd: str | None = None,
    tail_noise_max: int = 0,
) -> list[PsRow]:
    """
    Ground-truth process table: static rows from ps_aux minus capture ps/shell
    lines for this session, plus emulated -bash and (for aux/ef) the ps listing
    process. ``purpose`` is ``aux``, ``ef``, or ``top``.
    """
    from cowrie.core import utils

    rows = _filtered_ps_aux_base(protocol)
    rows.append(_make_session_shell_row(protocol, utils))
    if purpose in ("aux", "ef"):
        cmd = ps_display_cmd or ("ps aux" if purpose == "aux" else "ps -ef")
        ps_row = _make_synthetic_ps_row(protocol, cmd, utils)
        protocol._gt_synthetic_ps_row = ps_row  # type: ignore[attr-defined]
        rows.append(ps_row)
    elif purpose == "top":
        snap = getattr(protocol, "_gt_synthetic_ps_row", None)
        if snap is not None:
            rows.append(snap)
    if purpose == "aux" and tail_noise_max > 0:
        n = random.randint(0, tail_noise_max)
        rows.extend(_aux_tail_noise(rows, n))
    return rows


def ps_aux_tail_noise_max_config() -> int:
    try:
        n = int(CowrieConfig.get("shell", "ps_aux_tail_noise_max", fallback="0"))
    except ValueError:
        return 0
    return max(0, min(n, 8))


def aux_cpu_time_to_ef(t: str) -> str:
    """Convert ps aux TIME to ps -ef TIME column (hh:mm:ss style)."""
    t = t.strip()
    if not t:
        return "00:00:00"
    parts = t.split(":")
    try:
        if len(parts) == 1:
            sec = int(parts[0])
        elif len(parts) == 2:
            a, b = int(parts[0]), int(parts[1])
            sec = a * 60 + b
        elif len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            sec = h * 3600 + m * 60 + s
        else:
            sec = 0
    except ValueError:
        sec = 0
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def aux_time_to_top_timeplus(t: str) -> str:
    t = t.strip()
    if not t:
        return "0:00.00"
    parts = t.split(":")
    try:
        if len(parts) == 2:
            a, b = int(parts[0]), int(parts[1])
            total = a * 60 + b
        elif len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            total = h * 3600 + m * 60 + s
        else:
            total = int(parts[0])
    except ValueError:
        total = 0
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}.00"


def _stat_pr_ni(stat: str) -> tuple[int, int]:
    if "<" in stat:
        return 0, -20
    if len(stat) >= 2 and stat[1] == "t":
        return 99, 0
    return 20, 0


def infer_ppids(rows: list[PsRow]) -> dict[int, int]:
    ordered = sorted(rows, key=lambda r: r.pid)
    ppid: dict[int, int] = {}

    listener: int | None = None
    for r in ordered:
        if "sshd:" in r.cmd and "listener" in r.cmd:
            listener = r.pid
            break

    for r in ordered:
        cmd = r.cmd
        if r.pid == 1:
            ppid[r.pid] = 0
        elif cmd.startswith("[kthreadd]"):
            ppid[r.pid] = 0
        elif cmd.startswith("["):
            ppid[r.pid] = 2
        elif "sshd-session:" in cmd and "[priv]" in cmd:
            ppid[r.pid] = listener if listener is not None else 1
        elif "sshd-session:" in cmd and "@" in cmd:
            m = re.search(r"sshd-session:\s*(\S+)@", cmd)
            if m:
                user = m.group(1)
                privs = [
                    p.pid
                    for p in ordered
                    if p.pid < r.pid
                    and "[priv]" in p.cmd
                    and f": {user} " in p.cmd
                ]
                ppid[r.pid] = max(privs) if privs else (listener or 1)
            else:
                ppid[r.pid] = listener or 1
        else:
            ppid[r.pid] = -1

    for r in ordered:
        if ppid.get(r.pid, -1) >= 0:
            continue
        cmd = r.cmd
        if "login --" in cmd:
            ppid[r.pid] = 1
        elif cmd.strip() == "-bash" or cmd.startswith("-bash"):
            if r.tty.startswith("pts/"):
                term = r.tty
                cands = [
                    p.pid
                    for p in ordered
                    if p.pid < r.pid
                    and "sshd-session:" in p.cmd
                    and f"@{term}" in p.cmd
                    and "[priv]" not in p.cmd
                ]
                ppid[r.pid] = max(cands) if cands else 1
            elif r.tty.startswith("tty"):
                logins = [
                    p.pid
                    for p in ordered
                    if p.pid < r.pid
                    and "login --" in p.cmd
                    and r.user in p.cmd
                ]
                ppid[r.pid] = max(logins) if logins else 1
            else:
                ppid[r.pid] = 1
        elif "sftp-server" in cmd:
            cands = [
                p.pid
                for p in ordered
                if p.pid < r.pid
                and "sshd-session:" in p.cmd
                and "notty" in p.cmd
                and r.user in p.cmd
                and "[priv]" not in p.cmd
            ]
            ppid[r.pid] = max(cands) if cands else 1
        elif "systemd --user" in cmd:
            ppid[r.pid] = 1
        elif "(sd-pam)" in cmd:
            cands = [
                p.pid
                for p in ordered
                if p.pid < r.pid
                and p.user == r.user
                and "systemd --user" in p.cmd
            ]
            ppid[r.pid] = max(cands) if cands else 1
        elif r.user != "root" and r.tty == "?" and any(
            x in cmd for x in ("dbus-daemon", "mpris-proxy")
        ):
            cands = [
                p.pid
                for p in ordered
                if p.pid < r.pid
                and p.user == r.user
                and "systemd --user" in p.cmd
            ]
            ppid[r.pid] = max(cands) if cands else 1
        elif "agetty" in cmd:
            ppid[r.pid] = 1
        elif "sleep" in cmd:
            bashes = [
                p.pid
                for p in ordered
                if p.pid < r.pid
                and p.user == r.user
                and "bash" in p.cmd
            ]
            ppid[r.pid] = max(bashes) if bashes else 1
        elif cmd.startswith("ps ") or cmd.endswith("ps aux"):
            bashes = [
                p.pid
                for p in ordered
                if p.pid < r.pid
                and p.user == r.user
                and ("bash" in p.cmd or "sshd-session" in p.cmd)
            ]
            ppid[r.pid] = max(bashes) if bashes else 1
        else:
            ppid[r.pid] = 1

    return ppid


def format_ps_ef(rows: list[PsRow], ppids: dict[int, int]) -> str:
    lines = ["UID          PID    PPID  C STIME TTY          TIME CMD\n"]
    for r in sorted(rows, key=lambda x: x.pid):
        pp = ppids.get(r.pid, 1)
        tty = r.tty
        tty_col = tty if len(tty) <= 8 else tty[:8]
        lines.append(
            f"{r.user:<12} {r.pid:>7} {pp:>7}  0 {r.start:<7} {tty_col:<8} "
            f"{aux_cpu_time_to_ef(r.time)} {r.cmd}\n"
        )
    return "".join(lines)


def _top_static_header_tail() -> str:
    """%Cpu / Mem / Swap / blank from capture (line 1–2 are dynamic)."""
    raw = load_ground_line("top_bn1.txt").splitlines()
    if len(raw) < 6:
        return "\n"
    return "\n".join(raw[2:6]) + "\n\n"


def format_top_bn1(protocol) -> str:
    from cowrie.core import utils

    rows = build_session_ps_rows(protocol, purpose="top")
    clock = time.strftime("%H:%M:%S", utils.shell_clock_tuple())
    up = utils.uptime(protocol.uptime())
    users = utils.shell_uptime_user_summary()
    load = protocol.get_shell_loadavg()

    line1 = (
        f"top - {clock} up {up},  {users},  load average: {load}\n"
    )
    run = sum(1 for r in rows if r.stat.startswith("R"))
    sleep = max(0, len(rows) - run)
    line2 = (
        f"Tasks: {len(rows)} total,{run:4d} running,{sleep:4d} sleeping,   0 stopped,   0 zombie\n"
    )
    # Keep %Cpu / Mem / Swap from capture for stable fingerprinting
    tail = _top_static_header_tail()
    body_lines = []
    body_lines.append(
        "    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND\n"
    )
    for r in sorted(rows, key=lambda x: x.pid):
        s = r.stat[0]
        pr, ni = _stat_pr_ni(r.stat)
        shr = min(r.rss, max(4096, (r.rss * 35) // 100))
        try:
            cpu = float(r.pcpu)
            mem = float(r.pmem)
        except ValueError:
            cpu, mem = 0.0, 0.0
        timep = aux_time_to_top_timeplus(r.time)
        cmd = r.cmd
        if len(cmd) > 100:
            cmd = cmd[:97] + "..."
        body_lines.append(
            f"{r.pid:7d} {r.user:<8} {pr:3} {ni:4} {r.vsz:7} {r.rss:7} {shr:7} "
            f"{s} {cpu:5.1f} {mem:5.1f}  {timep:>8} {cmd}\n"
        )
    return line1 + line2 + tail + "".join(body_lines)
