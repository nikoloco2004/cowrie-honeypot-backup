# Copyright (c) 2010 Upi Tamminen <desaster@gmail.com>
# See the COPYRIGHT file for more information

"""
cat command

"""

from __future__ import annotations

import getopt

from twisted.python import log

from cowrie.shell.command import HoneyPotCommand
from cowrie.shell.fs import FileNotFound

from custom_mem import memupdate

commands = {}

# Dynamic /proc files: Cowrie regenerates these in honeyfs before serving.
# Each value is a zero-argument callable that writes fresh content to the
# corresponding honeyfs path. Add new dynamic paths here as they're built.
DYNAMIC_PATHS = {
    "/proc/meminfo": memupdate.update,
    # "/proc/loadavg": loadupdate.update,
    # "/proc/uptime":  uptimeupdate.update,
    # "/proc/stat":    statupdate.update,
}

class Command_cat(HoneyPotCommand):
    """
    cat command
    """

    number = False
    linenumber = 1

    def start(self) -> None:
        try:
            optlist, args = getopt.gnu_getopt(
                self.args, "AbeEnstTuv", ["help", "number", "version"]
            )
        except getopt.GetoptError as err:
            self.errorWrite(
                f"cat: invalid option -- '{err.opt}'\nTry 'cat --help' for more information.\n"
            )
            self.exit()
            return

        for o, _a in optlist:
            if o in ("--help"):
                self.help()
                self.exit()
                return
            elif o in ("-n", "--number"):
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

                try:
                    # Virtual fs can serve stale A_CONTENTS from the pickle. After
                    # memupdate wrote honeyfs, read that file so values change "live".
                    if pname in DYNAMIC_PATHS:
                        fresh = memupdate.read_fresh_honeyfs_bytes(pname)
                        if fresh is not None:
                            contents = fresh
                        else:
                            contents = self.fs.file_contents(pname)
                    else:
                        contents = self.fs.file_contents(pname)
                    self.output(contents)
                except FileNotFound:
                    self.errorWrite(f"cat: {arg}: No such file or directory\n")
            self.exit()
        elif self.input_data is not None:
            self.output(self.input_data)
            self.exit()

    def output(self, inb: bytes | None) -> None:
        newline = True
        if inb is None:
            return
    
        null_pos = inb.find(b"\x00")
        if null_pos != -1:
            newline = False
            inb = inb[:null_pos]
    
        lines = inb.split(b"\n")
        if lines[-1] == b"":
            lines.pop()
        for line in lines:
            if self.number:
                self.write(f"{self.linenumber:>6}  ")
                self.linenumber = self.linenumber + 1
            else:
                if newline:
                    self.writeBytes(line + b"\n")
                else:
                    self.writeBytes(line)


    def lineReceived(self, line: str) -> None:
        """
        This function logs standard input from the user send to cat
        """
        log.msg(
            eventid="cowrie.session.input",
            realm="cat",
            input=line,
            format="INPUT (%(realm)s): %(input)s",
        )

        self.output(line.encode("utf-8"))

    def handle_CTRL_D(self) -> None:
        """
        ctrl-d is end-of-file, time to terminate
        """
        self.exit()

    def help(self) -> None:
        self.write(
            """Usage: cat [OPTION]... [FILE]...
Concatenate FILE(s) to standard output.

With no FILE, or when FILE is -, read standard input.

    -A, --show-all           equivalent to -vET
    -b, --number-nonblank    number nonempty output lines, overrides -n
    -e                       equivalent to -vE
    -E, --show-ends          display $ at end of each line
    -n, --number             number all output lines
    -s, --squeeze-blank      suppress repeated empty output lines
    -t                       equivalent to -vT
    -T, --show-tabs          display TAB characters as ^I
    -u                       (ignored)
    -v, --show-nonprinting   use ^ and M- notation, except for LFD and TAB
        --help     display this help and exit
        --version  output version information and exit

Examples:
    cat f - g  Output f's contents, then standard input, then g's contents.
    cat        Copy standard input to standard output.

GNU coreutils online help: <http://www.gnu.org/software/coreutils/>
Full documentation at: <http://www.gnu.org/software/coreutils/cat>
or available locally via: info '(coreutils) cat invocation'
"""
        )


commands["/bin/cat"] = Command_cat
commands["cat"] = Command_cat
