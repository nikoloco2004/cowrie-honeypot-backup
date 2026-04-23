# -*- test-case-name: cowrie.test.utils -*-
# Copyright (c) 2010-2014 Upi Tamminen <desaster@gmail.com>
# See the COPYRIGHT file for more information

from __future__ import annotations

import hashlib
import ipaddress
import time
from typing import TYPE_CHECKING, BinaryIO

from twisted.application import internet
from twisted.internet import endpoints

if TYPE_CHECKING:
    import configparser


def durationHuman(duration: float) -> str:
    """
    Turn number of seconds into human readable string
    """
    seconds: int = round(duration)
    minutes: int
    minutes, seconds = divmod(seconds, 60)
    hours: int
    hours, minutes = divmod(minutes, 60)
    days: float
    days, hours = divmod(hours, 24)
    years: float
    years, days = divmod(days, 365.242199)

    syears: str = str(years)
    sseconds: str = str(seconds).rjust(2, "0")
    sminutes: str = str(minutes).rjust(2, "0")
    shours: str = str(hours).rjust(2, "0")

    sduration: list[str] = []
    if years > 0:
        sduration.append("{} year{} ".format(syears, "s" * (years != 1)))
    else:
        if days > 0:
            sduration.append("{} day{} ".format(days, "s" * (days != 1)))
        if hours > 0:
            sduration.append(f"{shours}:")
        if minutes >= 0:
            sduration.append(f"{sminutes}:")
        if seconds >= 0:
            sduration.append(f"{sseconds}")

    return "".join(sduration)


def tail(the_file: BinaryIO, lines_2find: int = 20) -> list[bytes]:
    """
    From http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
    """
    lines_found: int = 0
    total_bytes_scanned: int = 0

    the_file.seek(0, 2)
    bytes_in_file: int = the_file.tell()
    while lines_2find + 1 > lines_found and bytes_in_file > total_bytes_scanned:
        byte_block: int = min(1024, bytes_in_file - total_bytes_scanned)
        the_file.seek(-(byte_block + total_bytes_scanned), 2)
        total_bytes_scanned += byte_block
        lines_found += the_file.read(1024).count(b"\n")
    the_file.seek(-total_bytes_scanned, 2)
    line_list: list[bytes] = list(the_file.readlines())
    return line_list[-lines_2find:]
    # We read at least 21 line breaks from the bottom, block by block for speed
    # 21 to ensure we don't get a half line


def uptime(total_seconds: float) -> str:
    """
    Gives a human-readable uptime string
    Thanks to http://thesmithfam.org/blog/2005/11/19/python-uptime-script/
    (modified to look like the real uptime command)
    """
    total_seconds = float(total_seconds)

    # Helper vars:
    MINUTE: int = 60
    HOUR: int = MINUTE * 60
    DAY: int = HOUR * 24

    # Get the days, hours, etc:
    days: int = int(total_seconds / DAY)
    hours: int = int((total_seconds % DAY) / HOUR)
    minutes: int = int((total_seconds % HOUR) / MINUTE)

    # 14 days,  3:53
    # 11 min

    s: str = ""
    if days > 0:
        s += str(days) + " " + ((days == 1 and "day") or "days") + ", "
    if len(s) > 0 or hours > 0:
        s += "{}:{}".format(str(hours).rjust(2), str(minutes).rjust(2, "0"))
    else:
        s += f"{minutes!s} min"
    return s


def init_factory_uptime_fakery(factory: object) -> None:
    """
    If [shell] fake_uptime_base is set, set fake_boot_epoch so emulated host uptime
    advances with wall clock instead of tracking only Cowrie process lifetime.
    """
    from cowrie.core.config import CowrieConfig

    base = CowrieConfig.get("shell", "fake_uptime_base", fallback="").strip()
    if not base:
        factory.fake_boot_epoch = None  # type: ignore[attr-defined]
        return
    try:
        b = float(base)
    except ValueError:
        factory.fake_boot_epoch = None  # type: ignore[attr-defined]
        return
    factory.fake_boot_epoch = time.time() - b  # type: ignore[attr-defined]


def shell_clock_tuple_for(ts: float | None = None) -> time.struct_time:
    """Convert Unix time to struct_time in display_timezone when configured."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from cowrie.core.config import CowrieConfig

    if ts is None:
        ts = time.time()
    tz_name = CowrieConfig.get("shell", "display_timezone", fallback="").strip()
    if tz_name:
        try:
            return datetime.fromtimestamp(ts, ZoneInfo(tz_name)).timetuple()
        except Exception:
            pass
    return time.localtime(ts)


def shell_clock_tuple() -> time.struct_time:
    """Wall clock 'now' for uptime/w; uses [shell] display_timezone when set."""
    return shell_clock_tuple_for(None)


def shell_loadavg_for_bucket(bucket: int) -> str:
    """Load triplet for a given time bucket (shared anchor across commands in one period)."""
    h = hashlib.blake2b(str(bucket).encode(), digest_size=16).digest()

    def frac(i: int) -> float:
        return (h[i] / 255.0) * 0.12 + (h[(i + 3) % 16] / 255.0) * 0.08

    a, b, c = frac(0), frac(4) * 0.88, frac(8) * 0.72
    return f"{a:.2f}, {b:.2f}, {c:.2f}"


def shell_loadavg() -> str:
    """Load triplet for the current wall-clock bucket (prefer protocol.get_shell_loadavg() in sessions)."""
    from cowrie.core.config import CowrieConfig

    period = int(CowrieConfig.get("shell", "loadavg_period_seconds", fallback="45"))
    period = max(15, period)
    return shell_loadavg_for_bucket(int(time.time() // period))


def shell_loadavg_or_static() -> str:
    from cowrie.core.config import CowrieConfig

    if CowrieConfig.get("shell", "fake_uptime_base", fallback="").strip():
        return shell_loadavg()
    return "0.00, 0.00, 0.00"


def shell_format_datetime(ts: float, fmt: str) -> str:
    """strftime in display_timezone when [shell] display_timezone is set."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from cowrie.core.config import CowrieConfig

    tz_name = CowrieConfig.get("shell", "display_timezone", fallback="").strip()
    if tz_name:
        try:
            return datetime.fromtimestamp(ts, ZoneInfo(tz_name)).strftime(fmt)
        except Exception:
            pass
    return time.strftime(fmt, time.localtime(ts))


def shell_uptime_user_summary() -> str:
    from cowrie.core.config import CowrieConfig

    if not CowrieConfig.get("shell", "fake_uptime_base", fallback="").strip():
        return "1 user"
    raw = CowrieConfig.get("shell", "fake_w_user_count", fallback="11").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 11
    n = max(1, n)
    return f"{n} user" if n == 1 else f"{n} users"


def get_endpoints_from_section(
    cfg: configparser.ConfigParser, section: str, default_port: int
) -> list[str]:
    listen_addr: str
    listen_port: int
    listen_endpoints: list[str] = []

    if cfg.has_option(section, "listen_endpoints"):
        return cfg.get(section, "listen_endpoints").split()

    if cfg.has_option(section, "listen_addr"):
        listen_addr = cfg.get(section, "listen_addr")
    else:
        listen_addr = "0.0.0.0"

    if cfg.has_option(section, "listen_port"):
        listen_port = cfg.getint(section, "listen_port")
    else:
        listen_port = default_port

    for i in listen_addr.split():
        try:
            addr = ipaddress.ip_address(i)
            if addr.version == 6:
                escaped = i.replace(":", r"\:")
                listen_endpoints.append(f"tcp6:{listen_port}:interface={escaped}")
            else:
                listen_endpoints.append(f"tcp:{listen_port}:interface={i}")
        except ValueError:
            listen_endpoints.append(f"tcp:{listen_port}:interface={i}")

    return listen_endpoints


def create_endpoint_services(reactor, parent, listen_endpoints, factory):
    for listen_endpoint in listen_endpoints:
        endpoint = endpoints.serverFromString(reactor, listen_endpoint)

        service = internet.StreamServerEndpointService(endpoint, factory)
        # FIXME: Use addService on parent ?
        service.setServiceParent(parent)
