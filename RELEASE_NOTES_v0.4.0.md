# Release v0.4.0 — Session-synthesized `ps aux` and proc-table coherence

These notes cover **only what is new in v0.4.0** relative to prior documented releases (v0.3.0 and earlier). They do not repeat anchor clock, `w`/`last`, or chunked `ps` I/O, which are already described in `README.md` and `PERSONAL_CHANGELOG_2026-04-23.md`.

---

## 1. Problem: verbatim `ps_aux.txt` could not match the live session

**Symptom.** With ground truth enabled, `ps aux` returned the **`ps_aux.txt` file literally** — byte-for-byte the same on every run. That created several realism and consistency failures under Red Team–style comparison:

1. **Static artifact.** The capture ends with a **`ps aux` process line** (fixed PID, TTY, user, START time). A second run still showed that same line instead of reflecting a new `ps` PID or wall clock.
2. **Session mismatch.** Plain `ps` (no flags) had already been taught to show **`get_emulated_shell_pid()`** and **`next_emulated_ps_pid()`** with TTY from **`SSH_TTY`**. The full `ps aux` listing still contained the **captured** interactive shell and **`ps aux`** row for **whoever ran the capture** (e.g. `pi` on `pts/1`), which need not match the current attacker (`root` on `pts/0`).
3. **Fingerprint.** Identical megabyte-class process listing every time, including the trailing probe line, is easy to classify as a **canned dump** rather than live procps output.

**Requirement.** Keep the **bulk** of the process table aligned with the real Pi capture (PIDs, kernel threads, daemons) while **rewriting** the rows that must reflect **this** SSH session: login shell and the `ps` listing process, with optional small variation at the tail.

---

## 2. Fix: build `ps aux` from parsed rows + session overrides

**Approach.** `ps_aux.txt` remains the **canonical source**, but only after **parsing** into `PsRow` objects (`get_ps_aux_rows()`). Output is **formatted** with `format_ps_aux_line()` instead of dumping the file.

**Pipeline (`build_session_ps_rows` in `src/cowrie/core/ps_coherence.py`):**

1. **Filter out** rows that must not appear verbatim:
   - Any **captured `ps` listing** (`ps … aux`, `ps … -ef`, `-e`/`-f` combinations) so the old trailing `ps aux` line is gone.
   - Any **interactive shell** on the **session TTY** (`-bash` / `bash` heuristics matching `protocol.get_ps_display_tty()`), so we do not duplicate the real pty’s shell from the snapshot when the honeypot replaces it.
2. **Append** a synthetic **`PsRow`** for **`-bash`** using **`get_emulated_shell_pid()`**, session username, TTY from **`get_ps_display_tty()`**, START from **`shell_clock_tuple_for(logintime)`**, VSZ/RSS/STAT cloned from a reference **pts/** `-bash` in the capture when possible.
3. **Append** a synthetic **`PsRow`** for the **`ps`** invocation using **`next_emulated_ps_pid()`**, **`shell_clock_tuple()`** for START, `R+`, and **COMMAND** = `ps <actual argv>` (e.g. `ps aux`). Store this row on **`protocol._gt_synthetic_ps_row`** for reuse by **`top`** (see below).
4. **Optional noise (aux only).** If `[shell] ps_aux_tail_noise_max` &gt; 0, append 0…N extra **`[kworker/…]`**-style lines with **new PIDs** and current **`HH:MM`**, so the tail is not bitwise static. Not applied to `ps -ef` / `top` so task counts stay stable unless you run `ps aux`.

**Emitter.** `Command_ps_gt.start()` (aux branch) calls **`format_ps_aux_output(rows)`** and still uses **`_ps_emit_lines`** chunking for SSH stability.

---

## 3. Problem: `ps -ef` / `top` drifted from the `ps aux` story

**Symptom.** After v0.3.0, **`ps -ef`** and **`top -bn1`** were built from **`get_ps_aux_rows()`** (raw parse of the file), while **`ps aux`** was still the **verbatim file**. That meant the **synthetic session rows** (shell + `ps`) and **filtered** capture lines in `ps aux` did not exist in the table used for **`ps -ef`** / **`top`**, so PIDs and row counts could **disagree** across tools.

**Fix.** Both **`ps -ef`** and **`format_top_bn1()`** now call **`build_session_ps_rows(..., purpose="ef"|"top")`**:

- **`ef`:** Same filtered base + session **`-bash`** + new synthetic **`ps`** row with COMMAND reflecting **`ps <args>`**; **`next_emulated_ps_pid()`** runs per `ps -ef` invocation; snapshot updated.
- **`top`:** Same filtered base + session **`-bash`** + **last** stored synthetic **`ps`** row from the most recent **`ps aux` / `ps -ef`** (if any), **no** automatic noise lines.

**Result.** Kernel/daemon PIDs stay capture-faithful; session lines are **shared** across viewers where intended.

---

## 4. Problem: `%MEM` and `VSZ` columns fused on wide VSZ values

**Symptom.** Formatter concatenated **`%MEM`** and **`VSZ`** (e.g. `{pmem:>4}{vsz:>7}`) without a guaranteed column gap when VSZ had no printf padding. For **seven-digit VSZ**, procps-style width leaves **no leading spaces** in the VSZ field. If `%MEM` ends with a digit (e.g. `0.5`), the next field `5248640` **abuts** it and renders like **`0.55248640`** — wrong columns and an obvious parse/fingerprint failure.

**Fix.** After formatting VSZ with **`>7`**, if the string does **not** start with a space, insert **one** space between **`%MEM`** and **VSZ**; otherwise keep the original tight join so shorter VSZ values still match the reference alignment.

---

## 5. Configuration

| Key | Section | Purpose |
|-----|---------|---------|
| `ps_aux_tail_noise_max` | `[shell]` | Max extra synthetic kworker lines per **`ps aux`** (0 = off); actual count uniform in **0…max**. |

---

## 6. Files touched (implementation)

- `src/cowrie/core/ps_coherence.py` — `format_ps_aux_line`, `format_ps_aux_output`, `build_session_ps_rows`, tail noise, **`format_top_bn1`** row source, VSZ/MEM gap fix.
- `src/cowrie/commands/rpi_ground.py` — **`Command_ps_gt`** aux/`ps -ef` branches use builder + formatter.
- `etc/cowrie.cfg` — documents **`ps_aux_tail_noise_max`**.

---

## 7. Operational note for SCALPEL

Red Team compares to a **headless** reference Pi. A capture rich in **desktop/dev** paths (e.g. editor remote agents) may still be **internally consistent** but **semantically** distant from the organizer image — that is a **content** choice separate from this release’s mechanics. This release fixes **session coherence** and **column integrity**; refreshing **`ps_aux.txt`** (and dependents) against **your** official baseline Pi remains the right way to align **story** with **probe environment**.
