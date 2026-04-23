# Cowrie on Raspberry Pi 5 (custom deployment)

This repository is a **git clone of [Cowrie](https://github.com/cowrie/cowrie)** with **local customizations** to run a **medium-interaction SSH honeypot** on a **Raspberry Pi 5** running **Debian 13 (trixie)**, and to make the emulated environment resemble that host for lab work and research.

- **Upstream:** [`cowrie/cowrie`](https://github.com/cowrie/cowrie) — `git remote` name: `origin`
- **This backup fork:** `git remote` name: `backup` → your GitHub copy (private), used to snapshot configuration and custom code
- **Baseline tag:** `v0.0.0` — clean snapshot before the Pi-5–specific work
- **This document’s release:** `v0.4.0` — session-built **`ps aux`** + proc-table coherence; see [Tags](#version-tags) and **`RELEASE_NOTES_v0.4.0.md`**

Official upstream documentation: [https://docs.cowrie.org/](https://docs.cowrie.org/)

---

## How this deployment works (short)

1. **Cowrie** listens for SSH (default **port 2222** in this config) and emulates a Linux shell, filesystem, and many commands in Python. Nothing here runs a real root shell for attackers; it is a **honeypot**.

2. **Configuration** is read from `etc/cowrie.cfg` (and defaults from `etc/cowrie.cfg.dist`). Logging goes under `var/log/cowrie/`, session artefacts under `var/lib/cowrie/`.

3. **Two layers of “looking like a Pi 5”**
   - **Baseline fingerprint:** kernel/uname, SSH version strings, `honeyfs` overlays, emulated `dmesg` — tuned to match the real machine.
   - **Optional `ground_truth` mode:** a set of **captured command outputs** (text files) from the real Pi, used when a command is implemented in `rpi_ground.py` and `[shell] ground_truth = pi5_debian13`.

4. **Python environment:** install with `python3 -m venv cowrie-env && source cowrie-env/bin/activate && pip install -e .`, then `cowrie start` / `cowrie stop`.

---

## What to change for different behaviours

### Listen address, port, enabled services

| Goal | Config location |
|------|-----------------|
| SSH listen port, bind address | `etc/cowrie.cfg` → `[ssh]` → `listen_endpoints` (e.g. `tcp:2222:interface=0.0.0.0`) |
| Telnet | `[telnet]` → `enabled`, `listen_endpoints` |
| Hostname shown in the fake shell | `[honeypot]` → `hostname` |
| Honeypot user/password | `etc/userdb.txt` |

### Fingerprint (uname, banners, `ssh -V` in shell, wire SSH banner)

| Goal | Config / file |
|------|----------------|
| `uname -a` fields | `etc/cowrie.cfg` → `[shell]`: `kernel_version`, `kernel_build_string`, `hardware_platform`, `operating_system` |
| `uname -i` / `uname -p` | `uname_hw_platform`, `uname_processor` in `[shell]` |
| `arch` / fake ELF for `file` | `[shell]` → `arch` (e.g. `linux-aarch64-lsb`) |
| In-shell `ssh -V` string | `[shell]` → `ssh_version` |
| Client-visible SSH id string | `[ssh]` → `version` |
| Login / issue text | `honeyfs/etc/issue`, `issue.net`, `motd` |
| Overlays for `/etc/os-release`, `passwd`, `group`, `/proc/...` | `honeyfs/...` (merged over the emulated fs) |
| Emulated `dmesg` | `src/cowrie/data/txtcmds/bin/dmesg` |

### Ground truth (captured “real” command output)

| Goal | Where |
|------|--------|
| Turn on / off | `etc/cowrie.cfg` → `[shell]` → `ground_truth` = `pi5_debian13` or `none` |
| Replace captures (IP, PIDs, `top`, etc. changed) | `src/cowrie/data/ground_truth/pi5_debian13/*.txt` — see **`src/cowrie/data/ground_truth/pi5_debian13/README.md`** for regeneration hints |
| Loader | `src/cowrie/core/ground_truth.py` |
| Subclass overrides + extra commands (ip, lscpu, …) | `src/cowrie/commands/rpi_ground.py` |
| Tweak in-place (before overrides) | `src/cowrie/commands/uname.py`, `src/cowrie/commands/wget.py` (small ground-truth hooks) |

**Important:** The module `rpi_ground` is listed **last** in `src/cowrie/commands/__init__.py` so it can **replace** the default handler for the same command name. With `ground_truth = none`, most wrappers call the **original** Cowrie implementation via `super().call()`.

### Adding a new emulated command

1. See how existing commands are registered in `src/cowrie/commands/*.py` (`commands["name"] = CommandClass`).
2. Either add a new file and import it in `commands/__init__.py`, or append to a suitable module.
3. If it should be ground-truth–driven, add a text file under `data/ground_truth/pi5_debian13/` and a small class in `rpi_ground.py` (or a dedicated module loaded after stock commands).

### Logs and forensics

| Output | Path |
|--------|------|
| JSON events | `var/log/cowrie/cowrie.json` |
| Text log | `var/log/cowrie/cowrie.log` |
| TTY session logs | `var/lib/cowrie/tty/` (replay: `playlog`) |
| Downloaded “files” from attackers | `var/lib/cowrie/downloads/` |

---

## Version tags

| Tag | Meaning |
|-----|---------|
| **v0.0.0** | Initial copy pushed to your GitHub backup; baseline before Pi 5 high-fidelity work. |
| **v0.1.0** | Adds ground-truth system, `rpi_ground`, `README.md` (this file), and `PERSONAL_CHANGELOG_2026-04-23.md`. |
| **v0.2.0** | Ground-truth `ps` streams in chunks (SSH stability), real `honeyfs/etc/os-releases` (no broken symlink), aligned `/etc` and `/proc` honeyfs, `home` / `opt` / `root` lab overlays, updated `fs.pickle`. |
| **v0.3.0** | Emulated host **anchor**: `fake_uptime_base` + `display_timezone`, dynamic `/proc/uptime`, session-cached **load average** (`uptime` matches `w`), Debian-style **`w`** + decoy rows, synthetic **`last`** tied to the same boot time when ground truth + fake uptime are enabled. **`ps -ef`** / **`top -bn1`** are built from **`ps_aux`** so **PIDs match**. |
| **v0.4.0** | **`ps aux`** is **synthesized** from parsed `ps_aux` rows plus session **`-bash`** / **`ps`** lines (emulated PIDs, real argv); **`ps -ef`** / **`top`** use the **same** session table; optional **`ps_aux_tail_noise_max`**; **`format_ps_aux_line`** fix for **`%MEM`** vs **7-digit VSZ** collision. Details: **`RELEASE_NOTES_v0.4.0.md`**. |

Restore a tree: `git checkout v0.4.0` (or `v0.3.0`, `v0.2.0`, `v0.1.0`, `v0.0.0`).

---

## Changelog (summary)

### v0.4.0

- **`ps aux`:** Built from **`get_ps_aux_rows()`** with filters + session **`PsRow`** injection; not a verbatim **`ps_aux.txt`** dump. See **`RELEASE_NOTES_v0.4.0.md`** (problem/solution narrative).
- **Cross-tool table:** **`ps -ef`** and **`top -bn1`** use **`build_session_ps_rows`** so the session shell / last **`ps`** snapshot align with **`ps aux`**.
- **Config:** **`ps_aux_tail_noise_max`** in **`[shell]`** (optional kworker tail noise on **`ps aux`** only).
- **Cursor:** **`.cursor/rules/scalpel-hackathon.mdc`** — Project SCALPEL scoring and design constraints for agents.

### v0.3.0

- **Anchor clock:** `[shell]` options `display_timezone`, `fake_uptime_base`, `fake_proc_idle_*`, `fake_w_user_count`, `loadavg_period_seconds` keep `date`, `uptime`, and `cat /proc/uptime` coherent; **`get_shell_loadavg()`** on the session caches load for the current period so **`uptime` and `w` agree**.
- **`last`:** With `ground_truth = pi5_debian13` and fake uptime, **`last`** prints plausible `reboot` / `still logged in` / `wtmp begins` lines derived from **`fake_boot_epoch`** instead of a static “not found” error.
- **PID coherence (v0.3.0 baseline):** **`ps -ef`** and **`top -bn1`** derived from parsed **`ps_aux`** (`core/ps_coherence.py`). *v0.4.0 extends this to a unified session table and synthesized **`ps aux`** output — see above.*
- **Docs:** **`PERSONAL_CHANGELOG_2026-04-23.md`** v0.3.0 postscript and PID section.

### v0.2.0

- **Ground truth / SSH:** Large `ps aux` / `ps -ef` output is sent in line batches (reactor scheduling) so clients do not reset the session; `cat /etc/os-release` works via a real `honeyfs/etc/os-release` file (replacing a broken symlink).
- **Honeyfs / pickle:** Refreshed `passwd`, `group`, `shadow`, `hosts`, `hostname`, `issue` files, and proc snapshots; added lab-style tree under `honeyfs/home/`, `honeyfs/opt/`, and `honeyfs/root/`; `fs.pickle` updated to match. **If this repo is ever public, audit those trees for placeholder secrets** (e.g. `.env`, `authorized_keys`).
- **Docs:** this section and the v0.2.0 postscript in **`PERSONAL_CHANGELOG_2026-04-23.md`**.

### v0.1.0

- **Ground truth:** `ground_truth` mode with packaged captures and `rpi_ground` command layer.
- **Config:** `uname` split, optional Pi-style `id` for user `pi`, `wget` error line for a fake long option.
- **Honeyfs / data:** Trixie-like `/etc` and `/proc` overlays; full `dmesg` text capture.
- **Docs:** this `README` and a detailed narrative in **`PERSONAL_CHANGELOG_2026-04-23.md`**.

For the full “what and why” story, read **`PERSONAL_CHANGELOG_2026-04-23.md`**.

---

## Security note

This README does not contain live credentials. Keep **SSH keys, Wi‑Fi passwords, and honeypot `userdb` secrets** out of public repos. Use private repositories and environment-specific configuration where needed.

---

## License

Cowrie is **BSD-3-Clause**; see `LICENSE.rst`. Your customizations in this tree are a derivative deployment; keep upstream copyright and license notices when redistributing.
