# Personal change log — Cowrie on Raspberry Pi 5 (2025–2026)

This file is a **narrative record** of what was done to this tree and **why**, for your own notes. It is not the upstream Cowrie changelog.

---

## Context

- **Host:** Raspberry Pi 5, Debian GNU/Linux 13 (trixie), kernel `6.12.75+rpt-rpi-2712`, aarch64.
- **Goal:** Run Cowrie (medium-interaction SSH honeypot) on that Pi, back the configuration to your GitHub fork, and gradually make the **emulated shell** match the real OS so probes and lab checks look consistent.
- **Upstream remote:** `origin` → `https://github.com/cowrie/cowrie.git` (unchanged).
- **Your backup remote:** `backup` → `https://github.com/nikoloco2004/cowrie-honeypot-backup.git`.

---

## GitHub backup and versioning

**Why:** Keep a private copy of the full project history and a tag you can reset to if experiments go wrong.

**What we did**

- Installed/used `gh` (GitHub CLI) and created the private repo on your account, added remote `backup`, pushed branches/tags.
- Set **local** git `user.name` / `user.email` in this clone (GitHub noreply) so annotated tags work.
- Tagged **`v0.0.0`** as the initial baseline (release “V0.0 — Baseline” on GitHub) at commit `cd0770d3` before heavy customization, so you can always `git checkout v0.0.0` to a pre-tweak state.

**Later (this session):** tag **`v0.1.0`** after Pi 5 “ground truth” work and documentation; see that tag and `README.md` for operator instructions.

---

## Fingerprint: honeypot looks like the real Pi (first pass)

**Why:** Default Cowrie emulates an old 32/64-bit x86 Debian 7 style image. Your real machine is **aarch64 Pi OS**; you wanted `uname`, banners, and key files to match the physical Pi for consistency and plausibility.

**What we did**

- Edited `etc/cowrie.cfg` `[shell]`: `arch`, `kernel_version`, `kernel_build_string`, `hardware_platform`, `ssh_version` (in-shell), and `[ssh] version` (wire banner) to match the Pi 5.
- **Honeyfs overlay** (`honeyfs/`): updated `issue`, `issue.net`, `hostname`, added `os-release`, `debian_version`, and **proc** snapshots (`cpuinfo`, `meminfo`, `uptime`, `version`) and devicetree `model` path.
- Replaced the emulated `dmesg` text (`src/cowrie/data/txtcmds/bin/dmesg`) with a capture of the real host’s `dmesg` (long file).

---

## “Ground truth” mode (Debian 13 / Pi 5–aligned command output)

**Why:** A written spec asked for many commands (network tools, `ps`, `lscpu`, `systemctl`, etc.) to **match a real Trixie/Pi5 shell** in wording, line breaks, and error messages where possible, using captured output instead of hand-written guesses.

**What we did**

1. **`src/cowrie/core/ground_truth.py`**  
   - Reads text files from `src/cowrie/data/ground_truth/pi5_debian13/`.

2. **`etc/cowrie.cfg` `[shell]`**  
   - `ground_truth = pi5_debian13` to turn the mode on.  
   - `uname_hw_platform` / `uname_processor` for correct `uname -i` / `-p` (GNU uname split).

3. **`src/cowrie/commands/uname.py` (in-place edit)**  
   - Separated `-m`, `-p`, `-i`; `uname -a` does **not** include `-i`/`-p` (GNU behaviour).

4. **`src/cowrie/commands/wget.py` (in-place edit)**  
   - If `ground_truth` is on and `--totally-fake-flag` is used, print the captured `wget` error and exit (matches real `wget` complaint).

5. **`src/cowrie/commands/rpi_ground.py` (new)**  
   - Imported **last** in `commands/__init__.py` so it **overrides** the global `commands` table for:  
     `ifconfig`, `netstat` (for `-rn` + numeric route dump), `ps` (`ps aux` / `ps -ef`), `which`, `id` (for user `pi`), `service --status-all`, and adds implementations for `lsb_release`, `hostnamectl`, `vcgencmd`, `lscpu`, `ip`, `ss`, `top -bn1`, `systemctl` (subset), `insmod`, `make` (kbuild error path), `last` / `lastlog` as *command not found* to match a minimal image.  
   - When `ground_truth = none`, most wrappers call **`super().call()`**; tools only added here print “command not found” if that binary wouldn’t exist in stock Cowrie.

6. **Captures in `data/ground_truth/pi5_debian13/`**  
   - Generated on the Pi with real commands; **refresh** that directory if the OS or network changes and you need a new snapshot.  
   - Includes `README.md` with a regeneration shell snippet.

7. **Honeyfs**  
   - `passwd` and `group` replaced from captures so `cat /etc/passwd` / `group` look like the reference system.

**Caveats we accepted**

- Exit codes / `$?` are only partially meaningful in Cowrie.  
- DHCP-dependent values are **snapshots** until you re-run captures.  
- Not every command in the spec is specialized (e.g. complex `dd`/`kmem` pipelines may still fall through to generic or partial behaviour).

---

## Files worth knowing (quick index)

| Area | Path |
|------|------|
| Main config | `etc/cowrie.cfg` |
| Honeypot creds | `etc/userdb.txt` |
| Ground-truth switch + uname extras | `[shell]` in `etc/cowrie.cfg` |
| Pi5 text captures | `src/cowrie/data/ground_truth/pi5_debian13/` |
| Subclass “override” commands | `src/cowrie/commands/rpi_ground.py` |
| Uname / wget behaviour | `src/cowrie/commands/uname.py`, `wget.py` |
| Emulated dmesg | `src/cowrie/data/txtcmds/bin/dmesg` |
| Login/issue overlay | `honeyfs/etc/*`, `honeyfs/proc/`, `honeyfs/sys/.../model` |
| Command registry order | `src/cowrie/commands/__init__.py` (loads `rpi_ground` last) |
| Fork layout since `v0.0.0` | **`RELEASE_NOTES_v0.4.1.md`** (categorized map) |

---

## Why some changes are “overrides” vs “edits”

- **Edited in place:** `uname.py`, `wget.py` (small, stable hooks).  
- **Overrides via subclasses:** `rpi_ground.py` re-registers the same command names after the stock modules, so your fork keeps upstream `ifconfig.py` / `base.py` (for `ps`) / etc. readable, but **runtime** uses the subclass when `ground_truth` is on.

This split makes merges from upstream a bit easier, except where you must resolve conflicts in `uname.py` / `wget.py` / `__init__.py` / `cowrie.cfg`.

---

## Postscript (v0.1.0 publish)

- Committed all of the above as **`a4b16f63`** on `main`, tagged **`v0.1.0`**, pushed to **`backup`** (`nikoloco2004/cowrie-honeypot-backup`).
- Added root **`README.md`** (GitHub landing) and this file; **`etc/cowrie.cfg`** was **force-added** to the repo for this fork (it was listed in `.gitignore` as `cowrie.cfg` so it would not normally be committed). If you ever make the repo public, audit that file for anything sensitive.
- GitHub release: [v0.1.0](https://github.com/nikoloco2004/cowrie-honeypot-backup/releases/tag/v0.1.0).

---

## Postscript (v0.2.0 publish)

**Why:** Finish snapshotting the working tree (honeyfs + virtual FS pickle), document the ground-truth `ps` / `os-release` fixes, and cut a tag you can reference for a stable restore point.

**What we did**

- **SSH + ground truth:** `rpi_ground.Command_ps_gt` now streams `ps aux` / `ps -ef` captures in small line batches with `reactor.callLater(0, …)` so one huge `write()` no longer drops SSH sessions. `honeyfs/etc/os-release` is a regular file (same content as the capture) because a broken symlink there made `cat /etc/os-release` print nothing.
- **Honeyfs / `fs.pickle`:** Committed updates to `group`, `hostname`, `hosts`, `issue`, `issue.net`, `passwd`, `shadow`, `proc/modules`, `proc/mounts`, `proc/net/arp`, and regenerated `src/cowrie/data/fs.pickle` so the emulated filesystem matches the overlays.
- **Lab overlays:** Added `honeyfs/home/` (user profile/history stubs), `honeyfs/opt/` (sample app tree), and `honeyfs/root/` (root shell artefacts) for richer session interaction. **Treat as sensitive** if those paths ever contain real keys or secrets; this backup repo is intended to stay **private** unless scrubbed.
- **Git:** Release commit **`c49f9155`** on `main`, tag **`v0.2.0`**, push to **`backup`** with `git push backup main && git push backup v0.2.0`. GitHub tag: [v0.2.0](https://github.com/nikoloco2004/cowrie-honeypot-backup/releases/tag/v0.2.0) (create a Release from the tag if you want release notes in the UI).
- **Docs:** `README.md` version table and changelog section updated for v0.2.0.

---

## Postscript (v0.3.0 publish)

**Why:** Probes compare `date`, `uptime`, `cat /proc/uptime`, `w`, and `last`. Without a single emulated **boot anchor** and **one load snapshot per time bucket**, outputs disagree (e.g. different load on `uptime` vs `w`, or `last` missing), which weakens deception.

**What we did**

1. **Session-cached load average** — `HoneyPotBaseProtocol.get_shell_loadavg()` stores the triplet for the current `loadavg_period_seconds` wall bucket so every command in that SSH session reports the **same** load until the bucket advances (`src/cowrie/shell/protocol.py`). `utils.shell_loadavg_for_bucket()` centralizes the hash (`src/cowrie/core/utils.py`).
2. **`uptime` / `w`** — Call `protocol.get_shell_loadavg()` instead of `shell_loadavg_or_static()` (`uptime.py`, `base.py`, `rpi_ground.Command_w_gt`).
3. **`shell_format_datetime()`** — strftime in `display_timezone` for shared formatting (`utils.py`); used by synthetic `last`.
4. **`Command_last_gt`** — When `ground_truth = pi5_debian13` and `fake_boot_epoch` is set (`[shell] fake_uptime_base`), `last` prints **reboot** at the synthetic boot time, several **still logged in** rows (current user + decoy `pi` sessions with login times between boot and now), and **`wtmp begins`** at boot. If ground truth is off or fake boot is unset, behavior falls back to stock `last` (`src/cowrie/commands/rpi_ground.py`).
5. **Docs** — This postscript; **`README.md`** tag table and changelog for **v0.3.0**.

**Git:** Commit on `main`, annotated tag **`v0.3.0`**, push **`backup`** (`git push backup main && git push backup v0.3.0`). Create a GitHub Release from the tag if you want UI release notes.

---

## Postscript (v0.4.0 publish)

**Why (Project SCALPEL context).** Red Team runs the **same probes** against the honeypot and a **clean headless baseline Pi**. Demerits hit **behavioral inconsistency**: e.g. plain `ps` showing one shell PID and `ps aux` still containing the **capture’s** shell and **`ps aux`** line on another TTY/PID, or **`ps aux`** returning the **identical** megabyte capture every time including a stale trailing **`ps`** row. Separately, after v0.3.0, **`ps -ef`** / **`top`** used **parsed** rows while **`ps aux`** was still the **raw file**, so the **process table could disagree** across commands.

**What we did (code, summarized — full technical narrative in `RELEASE_NOTES_v0.4.0.md`):**

1. **`build_session_ps_rows(protocol, purpose=…)`** in **`ps_coherence.py`** — Start from **`get_ps_aux_rows()`**, drop captured **`ps` listing** rows and **session-TTY** interactive **`bash`** rows, append synthetic **`-bash`** (`get_emulated_shell_pid`) and **`ps`** (`next_emulated_ps_pid`, argv-matching **COMMAND**), store the latter on **`protocol._gt_synthetic_ps_row`** for **`top`**. Optional **`ps_aux_tail_noise_max`** adds 0…N cloned **`kworker`** lines with new PIDs (**`ps aux`** only).
2. **`format_ps_aux_line` / `format_ps_aux_output`** — Emit procps-shaped lines from **`PsRow`** instead of **`load_ground_line("ps_aux.txt")`** for the aux path. **`Command_ps_gt`** still chunks output for SSH.
3. **`ps -ef` / `top`** — Both call **`build_session_ps_rows`** (`ef` vs `top`) so the **same** filtered base + session rows back **`format_ps_ef`** and **`format_top_bn1`**.
4. **Column bugfix** — When **VSZ** fills seven digits, **`>7`** leaves no leading space; **`%MEM`** ending in a digit (e.g. `0.5`) **concatenated** to **`5248640`** produced **`0.55248640`**. We insert **one** space between **`%MEM`** and **VSZ** only when the formatted VSZ does **not** already start with a space.
5. **Docs / agent context** — **`RELEASE_NOTES_v0.4.0.md`** (release-only delta), **`README.md`** tag + changelog, **`.cursor/rules/scalpel-hackathon.mdc`** (SCALPEL scoring, baseline comparison, Cowrie-only rule).

**Git:** Commit on `main`, annotated tag **`v0.4.0`**, push **`backup`**. Paste **`RELEASE_NOTES_v0.4.0.md`** into the GitHub Release body for v0.4.0 if desired.

---

## Postscript (v0.4.1 publish)

**Why:** Presentations and new teammates need one place that answers “**what did we add since the clean baseline tag, and where does it live?**” without rereading every postscript.

**What we did**

- Added **`RELEASE_NOTES_v0.4.1.md`** — sections for docs/meta, **`etc/`**, core Python (**`ground_truth`**, **`ps_coherence`**, **`utils`**), **`protocol.py`**, command overrides (**`rpi_ground`**, **`uname`**, **`wget`**, **`base`**, **`uptime`**), the **`pi5_debian13/`** capture groups, **`honeyfs/`**, **`fs.pickle`**, **`txtcmds/bin/dmesg`**, and a **v0.0.0 → v0.4.0** tag summary table. Explicitly excludes upstream bulk and runtime **`var/`** noise.
- Updated **`README.md`** (current release pointer, version table, changelog) and this file’s quick index.

**Git:** Commit on `main`, annotated tag **`v0.4.1`**, push **`backup`**. Optional GitHub Release with body from **`RELEASE_NOTES_v0.4.1.md`**.

---

## Postscript (v0.4.2 publish)

**Why:** Honeyfs overlays, **`fs.pickle`**, **`cowrie.cfg`**, and split **`lsb_release`** captures existed only on the Pi working tree; the backup remote could not reproduce the same decoy filesystem without committing them.

**What we did**

- Staged **`honeyfs/etc/crontab`**, **`os-release`**, **`sys/firmware/devicetree/base/model`**, **`home/priyas/.ssh`**, **`home/ryanm/.ssh`**, **`proc/device-tree/{compatible,model,serial-number}`**, updated **`src/cowrie/data/fs.pickle`**, **`etc/cowrie.cfg`**.
- Added **`lsb_release_a.stdout.txt`** and **`lsb_release_a.stderr.txt`** under **`src/cowrie/data/ground_truth/pi5_debian13/`** (matching **`rpi_ground.Command_lsb_release`** + **`load_ground_line`**). Removed mistaken untracked copies under **`commands/`** and deleted zero-byte junk files **`exit`**, **`mkdir`**, **`touch`** at repo root.
- **`RELEASE_NOTES_v0.4.2.md`**, **`README`**, this postscript.

**Git:** Commit, tag **`v0.4.2`**, **`git push backup main && git push backup v0.4.2`**, optional **`gh release create`**.

---

## PID consistency (`ps`, `ps aux`, `ps -ef`, `top -bn1`)

**Why:** Ground-truth **`ps_aux.txt`**, **`ps_ef.txt`**, and **`top_bn1.txt`** came from different captures, so PIDs for the same logical processes (e.g. `sshd`) did not match — an easy honeypot fingerprint.

**What we did**

- Added **`src/cowrie/core/ps_coherence.py`**: parse **`ps_aux.txt`** as the single canonical table; **infer PPID** for `ps -ef` with heuristics (kernel threads, sshd listener/priv/sessions, login/getty/bash, systemd user slice, etc.); **format `ps -ef`** and **`top -bn1`** body from the same rows so every PID aligns with **`ps aux`**.
- **`Command_ps_gt`**: *v0.3.0:* **`ps aux`** was still the verbatim capture file; **`ps -ef` / `ps -e -f`** used synthetic **`format_ps_ef`**. *v0.4.0:* **`ps aux`** is **formatted from `PsRow` list** after session filters/injection; **`ps -ef`** uses **`build_session_ps_rows`** too — see **Postscript (v0.4.0)**.
- **`Command_top_cmd`**: batch **`top -b …`** uses **`format_top_bn1()`** — dynamic first line (clock/uptime/load/users), computed **Tasks** line, static **%Cpu/Mem/Swap** lines from the old **`top_bn1.txt`** capture; *v0.4.0:* process table rows from **`build_session_ps_rows(..., purpose="top")`** (includes last synthetic **`ps`** row when set).
- **Plain `ps` (no flags):** Stock Cowrie re-randomized **both** shell and `ps` PIDs when `server.process` was set. With **`ground_truth = pi5_debian13`**, **`Command_ps_gt`** now prints procps-style **`bash`** + **`ps`** rows: **one stable shell PID per session** (`get_emulated_shell_pid`), **only `ps` PID advances** per invocation (`next_emulated_ps_pid`), TTY from **`SSH_TTY`** when set else **`pts/0`**.

*End of personal log. For day-to-day operation and where to change things, see `README.md` in this repository.*
