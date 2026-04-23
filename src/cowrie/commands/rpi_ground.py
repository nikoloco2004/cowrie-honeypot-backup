# Copyright (c) 2026 Cowrie contributors
# Optional high-fidelity output for a Raspberry Pi 5 / Debian 13 (trixie) reference host.
# Enabled when [shell] ground_truth = pi5_debian13 in cowrie.cfg. Registers last and overrides
# some commands' implementations from earlier-included modules.
from __future__ import annotations

import getopt
import random
import re
import time

from twisted.internet import reactor

import cowrie.commands.last as _lastm
from cowrie.commands.base import Command_id, Command_ps, Command_w
from cowrie.commands.cat import Command_cat
from cowrie.commands.ifconfig import Command_ifconfig
from cowrie.commands.netstat import Command_netstat
from cowrie.commands.service import Command_service
from cowrie.commands.which import Command_which
from cowrie.core import ps_coherence, utils
from cowrie.core.config import CowrieConfig
from cowrie.core.ground_truth import ground_truth_enabled, load_ground_line
from cowrie.shell.command import HoneyPotCommand
from cowrie.shell.fs import FileNotFound

commands: dict = {}


def _gt() -> bool:
    return ground_truth_enabled()


def _w(s: str) -> str:
    if not s.endswith("\n"):
        return s + "\n"
    return s


# Absolute paths -> ground_truth file basename (full file read; not honeyfs/pickle)
_CAT_GT: dict[str, str] = {
    "/etc/os-release": "os-release.txt",
    "/proc/net/dev": "proc_net_dev.txt",
    "/sys/firmware/devicetree/base/model": "devicetree_model.txt",
}


def _dynamic_proc_uptime(protocol) -> bytes:
    fac = protocol.getProtoTransport().factory
    elapsed = time.time() - fac.starttime
    up1 = protocol.uptime()
    idle_b = float(CowrieConfig.get("shell", "fake_proc_idle_base", fallback="328656"))
    scale = float(CowrieConfig.get("shell", "fake_proc_idle_tick_scale", fallback="4.0"))
    idle = idle_b + elapsed * scale
    return f"{up1:.2f} {idle:.2f}\n".encode("utf-8")


# --- ifconfig + netstat + ps (wrap stock implementations) ---


class Command_ifconfig_gt(Command_ifconfig):
    def call(self) -> None:
        if not _gt():
            return super().call()
        self.write(_w(load_ground_line("ifconfig_a.txt")))


class Command_netstat_gt(Command_netstat):
    def call(self) -> None:
        if not _gt():
            return super().call()
        arg = "".join(self.args)
        if "r" in arg and "n" in arg:
            self.write(_w(load_ground_line("netstat_rn.txt")))
            return
        return super().call()


def _ps_ground_mode(args: list[str]) -> bool:
    a = " ".join(args)
    is_ef = bool(re.search(r"(^|\s)-ef($|\s)", a)) or (
        "-e" in args and "-f" in args
    )
    is_aux = "aux" in a or ({"a", "u", "x"}.issubset(set(args)))
    return bool(is_ef or is_aux or "u" in a)


def _ps_ef(args: list[str]) -> bool:
    a = " ".join(args)
    return bool(
        re.search(r"(^|\s)-ef($|\s)", a) or ("-e" in args and "-f" in args)
    )


class Command_ps_gt(Command_ps):
    """
    Ground-truth ps output is large; one write can reset SSH clients. Emit in
    line batches scheduled on the reactor so the session stays stable.
    """

    _PS_CHUNK_LINES = 32

    def start(self) -> None:
        if not _gt() or not _ps_ground_mode(self.args):
            return super().start()
        if _ps_ef(self.args):
            ps_disp = ("ps " + " ".join(self.args)).strip()
            rows = ps_coherence.build_session_ps_rows(
                self.protocol, purpose="ef", ps_display_cmd=ps_disp
            )
            pp = ps_coherence.infer_ppids(rows)
            text = _w(ps_coherence.format_ps_ef(rows, pp))
        else:
            noise_max = ps_coherence.ps_aux_tail_noise_max_config()
            rows = ps_coherence.build_session_ps_rows(
                self.protocol,
                purpose="aux",
                ps_display_cmd=("ps " + " ".join(self.args)).strip() or "ps aux",
                tail_noise_max=noise_max,
            )
            text = _w(ps_coherence.format_ps_aux_output(rows))
        lines = text.splitlines(keepends=True)
        self._ps_emit_lines(lines, 0)

    def call(self) -> None:
        if not _gt():
            return super().call()
        if _ps_ground_mode(self.args):
            return
        if self.args:
            return super().call()
        self._call_ps_plain_gt()

    def _call_ps_plain_gt(self) -> None:
        """
        Default `ps` (no options): procps-style header; shell PID stable per session;
        only the `ps` process PID changes each run (matches real Pi behavior).
        """
        tty = self.protocol.get_ps_display_tty()
        shell_pid = self.protocol.get_emulated_shell_pid()
        ps_pid = self.protocol.next_emulated_ps_pid()
        cmd = "ps"
        self.write("    PID TTY          TIME CMD\n")
        self.write(f"{shell_pid:7d} {tty:<11}00:00:00 bash\n")
        self.write(f"{ps_pid:7d} {tty:<11}00:00:00 {cmd}\n")

    def _ps_emit_lines(self, lines: list[str], idx: int) -> None:
        if idx >= len(lines):
            self.exit()
            return
        end = min(idx + self._PS_CHUNK_LINES, len(lines))
        self.write("".join(lines[idx:end]))
        reactor.callLater(0, self._ps_emit_lines, lines, end)  # type: ignore[attr-defined]


class Command_cat_gt(Command_cat):
    """
    Serve a few /proc and /sys paths from ground-truth files even if missing
    from the virtual fs or honeyfs merge.
    """

    def start(self) -> None:
        try:
            optlist, args = getopt.gnu_getopt(
                self.args, "AbeEnstTuv", ["help", "number", "version"]
            )
        except getopt.GetoptError as err:
            self.errorWrite(
                f"cat: invalid option -- '{err.opt}'\n"
                f"Try 'cat --help' for more information.\n"
            )
            self.exit()
            return

        for o, _a in optlist:
            if o in ("--help",):
                self.help()
                self.exit()
                return
            if o in ("-n", "--number"):
                self.number = True

        if len(args) > 0:
            for arg in args:
                if arg == "-":
                    self.output(self.input_data)
                    continue

                pname = self.fs.resolve_path(arg, self.protocol.cwd)

                if self.fs.isdir(pname):
                    self.errorWrite(f"cat: {arg}: Is a directory\n")
                    continue

                if _gt():
                    gfile = _CAT_GT.get(pname)
                    if gfile:
                        self.output(load_ground_line(gfile).encode("utf-8"))
                        continue

                if pname == "/proc/uptime" and (
                    _gt()
                    or CowrieConfig.get("shell", "fake_uptime_base", fallback="").strip()
                ):
                    self.output(_dynamic_proc_uptime(self.protocol))
                    continue

                try:
                    contents = self.fs.file_contents(pname)
                    self.output(contents)
                except FileNotFound:
                    self.errorWrite(
                        f"cat: {arg}: No such file or directory\n"
                    )
            self.exit()
        elif self.input_data is not None:
            self.output(self.input_data)
            self.exit()


class Command_id_gt(Command_id):
    def call(self) -> None:
        if not _gt():
            return super().call()
        if self.protocol.user.username == "pi":
            self.write(_w(load_ground_line("id_pi.txt")))
            return
        return super().call()


class Command_which_gt(Command_which):
    def call(self) -> None:
        if not _gt():
            return super().call()
        if not self.args or "PATH" not in self.environ:
            return
        for f in self.args:
            for part in self.environ["PATH"].split(":"):
                resolved = self.fs.resolve_path(f, part)
                if self.fs.exists(resolved):
                    self.write(f"{part}/{f}\n")


class Command_lsb_release(HoneyPotCommand):
    # def call(self) -> None:
    #     if not _gt():
    #         self.errorWrite("bash: lsb_release: command not found\n")
    #         return
    #     self.write(_w(load_ground_line("lsb_release_a.txt")))
    def call(self) -> None:
        if not _gt():
            # Match real "command not found" — verify exact format on ground truth
            self.errorWrite("bash: lsb_release: command not found\n")
            return
        
        # Emit stderr FIRST (matches real lsb_release ordering), then stdout
        stderr_output = load_ground_line("lsb_release_a.stderr.txt")
        stdout_output = load_ground_line("lsb_release_a.stdout.txt")
        
        if stderr_output:
            self.errorWrite(_w(stderr_output))
        if stdout_output:
            self.write(_w(stdout_output))


class Command_hostnamectl(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: hostnamectl: command not found\n")
            return
        self.write(_w(load_ground_line("hostnamectl.txt")))


class Command_vcgencmd(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: vcgencmd: command not found\n")
            return
        if not self.args:
            self.errorWrite("vcgencmd: no command given\n")
            return
        sub = self.args[0]
        if sub == "version":
            self.write(_w(load_ground_line("vcgencmd_version.txt")))
        elif sub == "measure_temp":
            t = 35.0 + random.random() * 20.0
            self.write(f"temp={t:.1f}'C\n")
        else:
            self.errorWrite(f"vcgencmd: command not supported\n")


class Command_lscpu_cmd(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: lscpu: command not found\n")
            return
        self.write(_w(load_ground_line("lscpu.txt")))


class Command_ip_cmd(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: ip: command not found\n")
            return
        s = " ".join(self.args)
        # Common shorthands: "ip a", "ip addr", "ip addr show"
        addrish = "route" not in s and "link" not in s and (
            re.search(r"(^|\s)(addr|address)(\s|$)", s)
            or s.strip() in ("a", "addr", "address")
            or (len(self.args) == 1 and self.args[0] in ("a", "addr"))
        )
        linkish = re.search(r"(^|\s)link(\s|$)", s) and "show" in s
        routeish = re.search(r"(^|\s)route(\s|$)", s) and "show" in s
        if addrish:
            self.write(_w(load_ground_line("ip_addr_show.txt")))
        elif linkish:
            self.write(_w(load_ground_line("ip_link_show.txt")))
        elif routeish:
            self.write(_w(load_ground_line("ip_route_show.txt")))
        else:
            self.errorWrite("Object \"addr\" is unknown, try \"ip help\".\n")


class Command_ss_cmd(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: ss: command not found\n")
            return
        if "-l" in self.args or "listening" in self.args or "tulnp" in "".join(
            self.args
        ):
            self.write(_w(load_ground_line("ss_tulnp.txt")))
        else:
            self.write("Netid State  Recv-Q Send-Q   Local Address:Port  Peer Address:PortProcess\n")


class Command_top_cmd(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: top: command not found\n")
            return
        a = " ".join(self.args)
        batch = "-b" in a and (
            re.search(r"(^|\s)-n\s+\d+(\s|$)", a) is not None
            or re.search(r"(^|\s)-n\d+(\s|$)", a) is not None
            or re.search(r"-\w*n\d+", a) is not None
            or ("-n" in self.args and any(x.isdigit() for x in self.args))
        )
        if batch:
            self.write(_w(ps_coherence.format_top_bn1(self.protocol)))
        else:
            self.write("top - running interactively (batch mode: top -b)\n")


class Command_systemctl_gt(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: systemctl: command not found\n")
            return
        s = " ".join(self.args)
        if "list-units" in s and "running" in s:
            self.write(_w(load_ground_line("systemctl_running.txt")))
        else:
            self.write("Unknown command verb\n")


class Command_service_gt(Command_service):
    def call(self) -> None:
        if not _gt():
            return super().call()
        if self.args and self.args[0] == "--status-all":
            self.write(_w(load_ground_line("service_status_all.txt")))
            return
        return super().call()


class Command_insmod(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: insmod: command not found\n")
            return
        if not self.args:
            self.errorWrite("insmod: missing filename\n")
            return
        self.errorWrite(load_ground_line("insmod_err.txt"))


class Command_make_kbuild(HoneyPotCommand):
    """
    Emulates: make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
    in /home/pi (error exit 2).
    """

    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: make: command not found\n")
            return
        t = " ".join(self.args)
        if "modules" in t and "M=" in t and "-C" in t:
            ttext = load_ground_line("make_kmodules_err.txt")
            for line in ttext.splitlines():
                if line.strip():
                    self.errorWrite(line + "\n")
            return
        self.errorWrite("make: Nothing to be done for 'all'.\n")


class Command_last_gt(HoneyPotCommand):
    """
    With fake_boot_epoch (see [shell] fake_uptime_base), emit last(1)-style lines
    tied to the same synthetic boot as date/uptime/w. Otherwise stock last.
    """

    def call(self) -> None:
        if not _gt():
            return _lastm.Command_last(self.protocol, *self.args).call()

        fac = self.protocol.getProtoTransport().factory
        fake_boot = getattr(fac, "fake_boot_epoch", None)
        if fake_boot is None:
            return _lastm.Command_last(self.protocol, *self.args).call()

        line = list(self.args)
        max_n: int | None = None
        while len(line):
            arg = line.pop(0)
            if not arg.startswith("-"):
                continue
            if arg == "-n" and line and line[0].isdigit():
                max_n = int(line.pop(0))

        boot_ts: float = fake_boot
        up = self.protocol.uptime()
        now = time.time()
        login_ts = self.protocol.logintime

        kernel = CowrieConfig.get(
            "shell", "kernel_version", fallback="6.12.75+rpt-rpi-2712"
        )[:19]

        pi_specs: list[tuple[str, str, float]] = [
            ("pts/2", "10.4.27.61", 0.93),
            ("pts/3", "10.4.27.68", 0.58),
            ("tty1", "-", 0.11),
        ]
        rows: list[tuple[float, str, str, str]] = []
        rows.append(
            (login_ts, self.protocol.user.username, "pts/0", self.protocol.clientIP)
        )
        for tty, host, frac in pi_specs:
            ts = boot_ts + up * frac
            ts = max(boot_ts + 90.0, min(ts, now - 45.0))
            rows.append((ts, "pi", tty, host))

        rows.sort(key=lambda r: r[0], reverse=True)
        if max_n is not None:
            rows = rows[: max(0, max_n)]

        for ts, user, tty, host in rows:
            self.write(
                "{:8s} {:12s} {:16s} {}   still logged in\n".format(
                    user,
                    tty,
                    host,
                    utils.shell_format_datetime(ts, "%a %b %d %H:%M"),
                )
            )

        self.write(
            "{:8s} system boot  {:16s} {}   still running\n".format(
                "reboot",
                kernel,
                utils.shell_format_datetime(boot_ts, "%a %b %d %H:%M"),
            )
        )
        self.write("\n")
        self.write(
            "wtmp begins "
            + utils.shell_format_datetime(boot_ts, "%a %b %d %H:%M:%S %Y")
            + "\n"
        )


class Command_lastlog_notfound(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: lastlog: command not found\n")
            return
        self.errorWrite(load_ground_line("lastlog_notfound.txt"))


class Command_w_gt(Command_w):
    """
    Debian/procps-style header and column spacing; decoy sessions from ground truth.
    """

    def call(self) -> None:
        if not _gt():
            return super().call()
        self.write(
            f" {time.strftime('%H:%M:%S', utils.shell_clock_tuple())} up {utils.uptime(self.protocol.uptime())},  {utils.shell_uptime_user_summary()},  load average: {self.protocol.get_shell_loadavg()}\n"
        )
        self.write(
            "USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU  WHAT\n"
        )
        u = self.protocol.user.username
        tty = "pts/0"
        frm = self.protocol.clientIP[:15].ljust(17)
        login = time.strftime(
            "%H:%M", utils.shell_clock_tuple_for(self.protocol.logintime)
        )
        self.write(f"{u:8}{tty:9}{frm}{login:8}    0.00s  0.00s  0.00s w\n")
        try:
            self.write(_w(load_ground_line("w_decoy_sessions.txt")))
        except OSError:
            pass


# --- registrations (override earlier command tables) ---

commands["/sbin/ifconfig"] = Command_ifconfig_gt
commands["ifconfig"] = Command_ifconfig_gt

commands["/bin/netstat"] = Command_netstat_gt
commands["netstat"] = Command_netstat_gt

commands["/bin/ps"] = Command_ps_gt
commands["ps"] = Command_ps_gt

commands["/bin/cat"] = Command_cat_gt
commands["cat"] = Command_cat_gt

commands["/usr/bin/id"] = Command_id_gt
commands["id"] = Command_id_gt

commands["which"] = Command_which_gt

commands["/usr/bin/lsb_release"] = Command_lsb_release
commands["lsb_release"] = Command_lsb_release

commands["/usr/bin/hostnamectl"] = Command_hostnamectl
commands["hostnamectl"] = Command_hostnamectl

commands["/usr/bin/vcgencmd"] = Command_vcgencmd
commands["vcgencmd"] = Command_vcgencmd

commands["/usr/bin/lscpu"] = Command_lscpu_cmd
commands["lscpu"] = Command_lscpu_cmd

commands["/usr/sbin/ip"] = Command_ip_cmd
commands["/sbin/ip"] = Command_ip_cmd
commands["ip"] = Command_ip_cmd

commands["/bin/ss"] = Command_ss_cmd
commands["/usr/bin/ss"] = Command_ss_cmd
commands["ss"] = Command_ss_cmd

commands["/usr/bin/top"] = Command_top_cmd
commands["/bin/top"] = Command_top_cmd
commands["top"] = Command_top_cmd

commands["/bin/systemctl"] = Command_systemctl_gt
commands["/usr/bin/systemctl"] = Command_systemctl_gt
commands["systemctl"] = Command_systemctl_gt

commands["/usr/sbin/service"] = Command_service_gt
commands["service"] = Command_service_gt

commands["/sbin/insmod"] = Command_insmod
commands["insmod"] = Command_insmod

commands["/usr/bin/make"] = Command_make_kbuild
commands["/bin/make"] = Command_make_kbuild
commands["make"] = Command_make_kbuild

commands["/usr/bin/last"] = Command_last_gt
commands["last"] = Command_last_gt

commands["/usr/bin/lastlog"] = Command_lastlog_notfound
commands["lastlog"] = Command_lastlog_notfound

commands["/usr/bin/w"] = Command_w_gt
commands["/bin/w"] = Command_w_gt
commands["w"] = Command_w_gt
