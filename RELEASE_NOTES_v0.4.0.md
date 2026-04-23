# Release v0.4.0 — Synthetic `ps aux`, session process rows, formatter fix

This note documents **only what is new since v0.3.0**. It does not repeat the anchored clock, session load average, synthetic `last`, or other items already described in `README.md` and `PERSONAL_CHANGELOG_2026-04-23.md` for earlier tags.

---

## 1. Problem

### 1.1 Static `ps aux` as a verbatim file

In v0.3.0, **`ps -ef`** and **`top -bn1`** were derived from parsed **`ps_aux.txt`** so PIDs matched a single canonical table, but **`ps aux` itself** still **printed the capture file literally**. That caused several issues under Project SCALPEL–style evaluation (honeypot vs baseline Pi, behavioral probes):

1. **Session fingerprint:** The capture’s last lines typically include someone else’s **TTY**, **shell PID**, and **`ps aux` PID** from the moment of capture. An attacker (or automated probe) comparing **plain `ps`** (session-aware PIDs introduced in development) with **`ps aux`** could see **inconsistent** session metadata: same SSH session but different shell PIDs or TTY in the long listing vs the short listing.

2. **Tape replay:** Running **`ps aux` twice** produced **byte-identical** output (aside from transport). Real systems show a **new PID** for the **`ps`** process each run and update **START/TIME** fields for interactive rows in line with the current clock. A perfect static dump is an easy **“canned output”** signal.

3. **Coherence gap:** The **synthetic `ps -ef` / `top`** body could not reflect the **same** injected session rows as `ps aux`, because `ps aux` never went through the shared builder—only the static file did.

### 1.2 Column corruption when reformatting rows (`%MEM` + `VSZ`)

To drop the verbatim file, each `PsRow` must be **serialized** back to a procps-like line. The first implementation concatenated **`%MEM`** (4-character field) and **`VSZ`** (7-character right-aligned field) with **no separator**.

When **`VSZ` is exactly seven digits**, the `>7` format produces **no leading spaces**. If **`%MEM` ends with a digit** (e.g. `0.5`) and **`VSZ` begins with a digit** (e.g. `5248640`), the two columns **visually merge** into one token (e.g. `0.55248640`). That is **wrong vs real `ps`**, breaks parsers that split on whitespace boundaries, and is a **high-confidence demerit** under behavioral accuracy checks.

---

## 2. Solution (v0.4.0)

### 2.1 Single session-aware table for `ps aux`, `ps -ef`, and `top`

All three paths now consume **`build_session_ps_rows()`** in `src/cowrie/core/ps_coherence.py`:

1. **Base rows:** Parsed from **`ps_aux.txt`** via **`get_ps_aux_rows()`**, then filtered:
   - Drop **captured `ps` listings** (`ps … aux`, `ps … -ef`, `-e`/`-f` combinations) so the stale “photographer’s” `ps` line is gone.
   - Drop **interactive shell rows** on the **current session TTY** (`SSH_TTY` → strip `/dev/` prefix, else `pts/0`) so we do not duplicate `-bash`/`bash` for the attacker’s pty.

2. **Injected rows (appended):**
   - **`-bash`:** **`get_emulated_shell_pid()`**, session username, **`get_ps_display_tty()`**, **START** from **`shell_clock_tuple_for(logintime)`**, VSZ/RSS/STAT cloned from a reference **pts** `-bash` in the capture when possible.
   - **`ps` command:** **`next_emulated_ps_pid()`**, **`R+`**, START from **`shell_clock_tuple()`**, **`CMD`** = actual argv (e.g. `ps aux`, `ps -ef`, `ps -a -u x`). The **`ps` row is stored on the protocol** as **`_gt_synthetic_ps_row`** so **`top`** can include the **last** listing process without re-advancing the PID sequence.

3. **Optional tail noise:** **`[shell] ps_aux_tail_noise_max`** (default `0`). If &gt; 0, each **`ps aux`** run may append **0…N** extra **`[kworker/…]`**-style lines with **new PIDs** and current **`HH:MM`**, so the listing is not always the same length. Noise is **not** added for **`ps -ef`** or **`top`** to avoid unnecessary task-count drift there.

4. **Emit:** **`format_ps_aux_output()`** = header + **`format_ps_aux_line()`** per row; **`Command_ps_gt`** still uses chunked writes for large output.

### 2.2 `%MEM` / `VSZ` boundary fix

**`format_ps_aux_line()`** now inserts an **explicit space** between **`%MEM`** and **`VSZ`** when the formatted VSZ string does **not** already start with a space (i.e. full 7-digit VSZ). Shorter VSZ values keep the original **abutted** layout so lines still match the reference capture for typical padded columns.

### 2.3 Protocol helpers (session PIDs / TTY)

**`HoneyPotBaseProtocol`** (`src/cowrie/shell/protocol.py`) now exposes:

- **`get_emulated_shell_pid()`** — stable per session (lazy random once).
- **`next_emulated_ps_pid()`** — advances with plausible gaps for each **`ps`** / **`ps aux`** / **`ps -ef`** synthetic process row.
- **`get_ps_display_tty()`** — from **`SSH_TTY`** or **`pts/0`**.

**`Command_ps_gt._call_ps_plain_gt()`** uses these for procps-style plain **`ps`** (no flags): **`bash`** + **`ps`**, matching the intended “real Pi” short listing behavior.

---

## 3. Files touched (v0.4.0)

| Path | Role |
|------|------|
| `src/cowrie/core/ps_coherence.py` | Session table builder, `format_ps_aux_*`, tail noise, `format_top_bn1` uses session rows |
| `src/cowrie/commands/rpi_ground.py` | `ps aux` / `ps -ef` use builder + formatters; plain `ps` ground path |
| `src/cowrie/shell/protocol.py` | Emulated shell/`ps` PIDs and display TTY |
| `etc/cowrie.cfg` | `ps_aux_tail_noise_max` |
| `.cursor/rules/scalpel-hackathon.mdc` | Persistent hackathon context for agents |
| `RELEASE_NOTES_v0.4.0.md` | This document |

---

## 4. Operational notes

- Regenerate **`ps_aux.txt`** on the reference Pi when the static part of the process tree should change; session rows are always **synthesized** from protocol state.
- For SCALPEL, align captures with the **headless baseline** story where possible; unrelated desktop tooling in captures is a separate narrative choice.
