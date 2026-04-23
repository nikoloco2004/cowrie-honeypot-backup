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
- **Git:** Single release commit on `main`, tag **`v0.2.0`**, push to **`backup`** with `git push backup main && git push backup v0.2.0`.
- **Docs:** `README.md` version table and changelog section updated for v0.2.0.

*End of personal log. For day-to-day operation and where to change things, see `README.md` in this repository.*
