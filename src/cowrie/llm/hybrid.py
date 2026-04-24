# ABOUTME: Optional LLM fallback when honeypot backend is shell and a command is not found.
# ABOUTME: Gated by [llm] hybrid_fallback; used only for simple single-segment, no-pipe, no-redirect lines.

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from twisted.internet import defer
from twisted.python import log

from cowrie.core.config import CowrieConfig
from cowrie.llm.llm import LLMClient
from cowrie.llm.protocol import strip_markdown

if TYPE_CHECKING:
    from collections.abc import Callable

    from cowrie.shell.honeypot import HoneyPotShell

_GIBBERISH_OK = re.compile(r"^[\s]*[A-Za-z0-9_./+:@%-]{1,64}[\s]*$")
# Pasted lines that include the fake prompt before the real argv0: user@host:path$cmd
_ARGV0_PROMPT_JUNK = re.compile(r".*@.+:.+\$.+")


def hybrid_fallback_enabled() -> bool:
    if CowrieConfig.get("honeypot", "backend", fallback="shell") != "shell":
        return False
    return CowrieConfig.getboolean("llm", "hybrid_fallback", fallback=False)


def _sanitize_command_token_pasted_prompt(raw: str) -> str:
    """
    If the user pasted 'pi@host:~$z9faketool' as one token, return 'z9faketool'.
    """
    s = raw.strip()
    if "$" in s and _ARGV0_PROMPT_JUNK.search(s) is not None:
        part = s.rsplit("$", 1)[-1].strip()
        if part and len(part) <= 64 and not part.startswith("("):
            if _GIBBERISH_OK.match(part) is not None or (
                not any(c.isspace() for c in part) and 1 <= len(part) <= 64
            ):
                return part
    return s


# Single-line stderr form only; if the model rambles, we discard it (see _force_one_line_not_found)
_BASH_NOT_FOUND_LINE = re.compile(
    r"^(-bash: |bash: )?.+: command not found!?\s*$", re.IGNORECASE
)


def _force_one_line_not_found(stripped: str, command: str) -> str:
    """
    Never show "helpful" multi-line LLM rants. Only accept one bash-shaped line, else static.
    """
    if not stripped:
        return f"-bash: {command}: command not found\n"
    first, _, rest = stripped.partition("\n")
    if rest.strip():
        log.msg("hybrid: discarding multi-line LLM output; using static not-found line")
        return f"-bash: {command}: command not found\n"
    line = first.strip()
    if len(line) > 200:
        log.msg("hybrid: discarding overlong LLM line; using static not-found line")
        return f"-bash: {command}: command not found\n"
    if not _BASH_NOT_FOUND_LINE.match(line):
        log.msg("hybrid: LLM line does not look like 'command not found'; using static")
        return f"-bash: {command}: command not found\n"
    # Never echo free-form model text; always the real bash-shaped line
    return f"-bash: {command}: command not found\n"


def _looks_like_gibberish_for_bash_not_found(name: str) -> bool:
    """
    If True, we skip the LLM and use static -bash: …: command not found.
    Heuristic: no alnum, too long, or very noisy tokens (gibberish), not a plausible argv0.
    """
    t = name.strip()
    if not t or len(t) > 64:
        return True
    if not any(c.isalnum() for c in t):
        return True
    if _GIBBERISH_OK.match(t) is None:
        return True
    return False


@defer.inlineCallbacks
def _run_llm_and_write(
    protocol: Any,
    shell: HoneyPotShell,
    command: str,
    rargs: list[str],
    run_or_prompt: Callable[[], None],
) -> defer.Deferred[None]:
    line = command if not rargs else f"{command} " + " ".join(rargs)
    client = LLMClient()
    max_tok = CowrieConfig.getint("llm", "hybrid_max_tokens", fallback=64)
    min_t, max_t = 8, 512
    if max_tok < min_t:
        max_tok = min_t
    elif max_tok > max_t:
        max_tok = max_t
    temp = CowrieConfig.getfloat("llm", "hybrid_temperature", fallback=0.15)
    if temp < 0.0:
        temp = 0.0
    elif temp > 2.0:
        temp = 2.0
    # Short system prompt = fewer prompt tokens; low max_tokens and temperature = faster on Ollama
    system_context = (
        f"Debian bash. Command not on PATH: {line!r}. "
        f"Output one stderr line only, e.g. -bash: {command}: command not found"
    )
    prompt = [system_context, f"User: {line}"]

    try:
        text = yield client.get_response(
            prompt, max_tokens=max_tok, temperature=temp
        )
    except Exception as e:
        log.err(f"hybrid LLM get_response: {e}")
        text = ""

    if not (text and text.strip()):
        text = f"-bash: {command}: command not found\n"
    else:
        text = _force_one_line_not_found(strip_markdown(text), command)

    protocol.terminal.write(text.encode("utf-8", errors="replace"))
    protocol.last_cmd_exit = 127

    run_or_prompt()

    from cowrie.shell import protocol as shell_protocol  # local

    if (
        isinstance(protocol, shell_protocol.HoneyPotExecProtocol)
        and not shell.cmdpending
    ):
        from twisted.internet import error
        from twisted.python import failure

        exit_status = failure.Failure(error.ProcessDone(status=""))
        protocol.terminal.transport.processEnded(exit_status)
    yield None  # for inlineCallbacks


def maybe_schedule_hybrid_unknown(
    shell: HoneyPotShell,
    cmd: dict[str, Any],
    cmd_array: list[dict[str, Any]],
    run_or_prompt: Callable[[], None],
) -> bool:
    """
    If hybrid fallback applies, start an async LLM request and return True.
    Caller must not run the synchronous command-not-found path when True.
    """
    if not hybrid_fallback_enabled():
        return False
    if len(cmd_array) != 1:
        return False
    if cmd.get("redirects"):
        return False
    if shell.redirect:
        return False
    argv0 = _sanitize_command_token_pasted_prompt(cmd["command"])
    if argv0 != cmd["command"]:
        log.msg(
            eventid="cowrie.hybrid.sanitize",
            input=f"{cmd['command']!r} -> {argv0!r}",
            format="hybrid argv0 sanitize: %(input)s",
        )
    if _looks_like_gibberish_for_bash_not_found(argv0):
        return False

    d = _run_llm_and_write(
        shell.protocol, shell, argv0, cmd.get("rargs", []), run_or_prompt
    )
    d.addErrback(log.err)
    return True
