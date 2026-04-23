# Copyright (c) 2009 Upi Tamminen <desaster@gmail.com>
# See the COPYRIGHT file for more information

from __future__ import annotations

import time

from cowrie.core import utils
from cowrie.shell.command import HoneyPotCommand

commands = {}


class Command_uptime(HoneyPotCommand):
    def call(self) -> None:
        self.write(
            "{}  up {},  {},  load average: {}\n".format(
                time.strftime("%H:%M:%S", utils.shell_clock_tuple()),
                utils.uptime(self.protocol.uptime()),
                utils.shell_uptime_user_summary(),
                self.protocol.get_shell_loadavg(),
            )
        )


commands["/usr/bin/uptime"] = Command_uptime
commands["uptime"] = Command_uptime
