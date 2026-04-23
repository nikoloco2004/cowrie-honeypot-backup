# Copyright (c) 2026 Cowrie contributors
# Optional high-fidelity output for a Raspberry Pi 5 / Debian 13 (trixie) reference host.
# Enabled when [shell] ground_truth = pi5_debian13 in cowrie.cfg. Registers last and overrides
# some commands' implementations from earlier-included modules.
from __future__ import annotations

import random
import re

import cowrie.commands.last as _lastm
from cowrie.commands.base import Command_id, Command_ps
from cowrie.commands.ifconfig import Command_ifconfig
from cowrie.commands.netstat import Command_netstat
from cowrie.commands.service import Command_service
from cowrie.commands.which import Command_which
from cowrie.core.ground_truth import ground_truth_enabled, load_ground_line
from cowrie.shell.command import HoneyPotCommand

commands: dict = {}


def _gt() -> bool:
    return ground_truth_enabled()


def _w(s: str) -> str:
    if not s.endswith("\n"):
        return s + "\n"
    return s


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


class Command_ps_gt(Command_ps):
    def call(self) -> None:
        if not _gt():
            return super().call()
        a = " ".join(self.args)
        is_ef = (
            bool(re.search(r"(^|\s)-ef($|\s)", a))
            or ("-e" in self.args and "-f" in self.args)
        )
        is_aux = "aux" in a or ({"a", "u", "x"}.issubset(set(self.args)))
        if is_ef:
            self.write(_w(load_ground_line("ps_ef.txt")))
        elif is_aux or "u" in a:
            self.write(_w(load_ground_line("ps_aux.txt")))
        else:
            return super().call()


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
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: lsb_release: command not found\n")
            return
        self.write(_w(load_ground_line("lsb_release_a.txt")))


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
        if "-b" in a and ("-n" in a or re.search(r"-n[0-9]+", a) or "n1" in a):
            self.write(_w(load_ground_line("top_bn1.txt")))
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


class Command_last_notfound(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            return _lastm.Command_last(self.protocol, *self.args).call()
        self.errorWrite(load_ground_line("last_notfound.txt"))


class Command_lastlog_notfound(HoneyPotCommand):
    def call(self) -> None:
        if not _gt():
            self.errorWrite("bash: lastlog: command not found\n")
            return
        self.errorWrite(load_ground_line("lastlog_notfound.txt"))


# --- registrations (override earlier command tables) ---

commands["/sbin/ifconfig"] = Command_ifconfig_gt
commands["ifconfig"] = Command_ifconfig_gt

commands["/bin/netstat"] = Command_netstat_gt
commands["netstat"] = Command_netstat_gt

commands["/bin/ps"] = Command_ps_gt
commands["ps"] = Command_ps_gt

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

commands["/usr/bin/last"] = Command_last_notfound
commands["last"] = Command_last_notfound

commands["/usr/bin/lastlog"] = Command_lastlog_notfound
commands["lastlog"] = Command_lastlog_notfound
