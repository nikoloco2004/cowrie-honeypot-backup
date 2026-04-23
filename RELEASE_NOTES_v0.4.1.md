# Release v0.4.1 — Repository map: fork layout since `v0.0.0`

This release is **documentation only**. It does not change honeypot behavior. It gives a **single categorized map** of where this tree differs from the **local baseline tag `v0.0.0`** (your “pre–Pi 5 customization” snapshot of this clone), and which **release tag** first introduced each major area.

**How to read “since v0.0.0”:** Anything listed here is **part of your fork’s Pi 5 / ground-truth / SCALPEL story**, or documentation supporting it. The bulk of **`src/cowrie/`** remains **upstream Cowrie**; only the paths called out below are the usual touch points for customization.

---

## 1. Top-level layout (mental model)

| Directory / file | Role |
|------------------|------|
| **`src/cowrie/`** | Python package: upstream Cowrie + **fork patches** (see §4–§6). |
| **`etc/`** | Runtime config committed in this fork (**`cowrie.cfg`**, **`userdb.txt`**). |
| **`honeyfs/`** | Files merged over the **emulated** filesystem (looks like `/` to the attacker). |
| **`var/`** | Logs, downloads, TTY captures at **runtime** — often **not** committed; don’t treat as “release artifacts.” |
| **Root docs** | **`README.md`**, **`PERSONAL_CHANGELOG_*.md`**, **`RELEASE_NOTES_v0.*.md`**. |
| **`.cursor/rules/`** | Cursor agent context (SCALPEL). |

---

## 2. Documentation and meta (fork)

| Path | Introduced | Purpose |
|------|------------|---------|
| **`README.md`** | **v0.1.0** | Operator overview: remotes, config tables, ground truth, version tags. Updated each release. |
| **`PERSONAL_CHANGELOG_2026-04-23.md`** | **v0.1.0** | Long-form “why we changed what” narrative; not upstream. |
| **`RELEASE_NOTES_v0.4.0.md`** | **v0.4.0** | Technical deep-dive: session-synthesized **`ps aux`**, shared process table, **`%MEM`/VSZ** fix. |
| **`RELEASE_NOTES_v0.4.1.md`** | **v0.4.1** | This file: **filesystem categorization** since **`v0.0.0`**. |
| **`.cursor/rules/scalpel-hackathon.mdc`** | **v0.4.0** | Project SCALPEL: scoring, baseline Pi comparison, Cowrie-only rule, consistency goals. |

---

## 3. Configuration and credentials

| Path | Introduced | Purpose |
|------|------------|---------|
| **`etc/cowrie.cfg`** | **v0.1.0+** (evolving) | Pi fingerprint (`uname`, `arch`, SSH strings), **`ground_truth`**, fake uptime / timezone / loadavg / **`w`** / **`last`**, **`ps_aux_tail_noise_max`**, listen ports, paths. **Force-added** to this fork (upstream often gitignores it). |
| **`etc/cowrie.cfg.dist`** | Upstream | Default template; diff against **`cowrie.cfg`** when upgrading. |
| **`etc/userdb.txt`** | Upstream pattern | Honeypot login allowlist; tune per deployment. |

---

## 4. Core Python (fork modules and edits)

| Path | Introduced | Purpose |
|------|------------|---------|
| **`src/cowrie/core/ground_truth.py`** | **v0.1.0** | Load text blobs from **`data/ground_truth/pi5_debian13/`** when **`ground_truth = pi5_debian13`**. |
| **`src/cowrie/core/ps_coherence.py`** | **v0.3.0** (expanded **v0.4.0**) | Parse **`ps_aux.txt`** → **`PsRow`**; infer PPID; format **`ps -ef`** / **`top`**, **`build_session_ps_rows`**, **`format_ps_aux_*`**, optional tail noise. |
| **`src/cowrie/core/utils.py`** | **v0.3.0** (fork edits) | Shell clock in **`display_timezone`**, **`shell_clock_tuple` / `_for`**, **`uptime()`** text helpers, **`shell_loadavg_for_bucket`**, **`shell_format_datetime`**, decoy **`w`** helpers, etc. |

---

## 5. Shell session behavior (fork)

| Path | Introduced | Purpose |
|------|------------|---------|
| **`src/cowrie/shell/protocol.py`** | **v0.3.0+** (fork edits) | **`get_shell_loadavg()`** (per-session bucket), **`get_emulated_shell_pid()`**, **`next_emulated_ps_pid()`**, **`get_ps_display_tty()`** from **`SSH_TTY`**. |

---

## 6. Command layer (fork overrides)

| Path | Introduced | Purpose |
|------|------------|---------|
| **`src/cowrie/commands/rpi_ground.py`** | **v0.1.0** (grew each tag) | **Ground-truth command overrides** when mode is on: **`ps`**, **`top`**, **`w`**, **`last`**, **`cat`** (incl. **`/proc/uptime`** path), **`ifconfig`**, **`netstat`**, **`ip`**, **`ss`**, **`lscpu`**, **`lsb_release`**, **`hostnamectl`**, **`systemctl`**, **`service`**, **`vcgencmd`**, **`which`**, **`id`**, **`insmod`**, **`make`**, **`wget`** hook surface, etc. Registers **`commands[...]`** last. |
| **`src/cowrie/commands/__init__.py`** | **v0.1.0** | Imports **`rpi_ground`** **after** stock modules so overrides win. |
| **`src/cowrie/commands/uname.py`** | **v0.1.0** | GNU-style **`-m` / `-p` / `-i`** split; **`uname -a`** shape. |
| **`src/cowrie/commands/wget.py`** | **v0.1.0** | Ground-truth error line for fake long flag (probe parity). |
| **`src/cowrie/commands/base.py`** | **v0.3.0** | Stock **`w`** / **`who`** path uses **`get_shell_loadavg()`** where applicable. |
| **`src/cowrie/commands/uptime.py`** | **v0.3.0** | Uses **`get_shell_loadavg()`** for load line consistency. |

---

## 7. Ground-truth capture corpus (`pi5_debian13`)

**Directory:** **`src/cowrie/data/ground_truth/pi5_debian13/`**  
**Introduced:** **v0.1.0** (files added/rotated over time; regenerate per **`README.md`** there).

| Group | Files (representative) |
|-------|-------------------------|
| **Identity / `/etc`** | `passwd.txt`, `group.txt`, `os-release.txt`, `debian_version.txt`, `hostname_uname.txt` |
| **Network** | `ifconfig_a.txt`, `ip_addr_show.txt`, `ip_link_show.txt`, `ip_route_show.txt`, `netstat_rn.txt`, `ss_tulnp.txt`, `proc_net_dev.txt` |
| **CPU / machine** | `proc_cpuinfo.txt`, `proc_meminfo.txt`, `proc_version.txt`, `lscpu.txt`, `devicetree_model.txt`, `model.txt`, `vcgencmd_*.txt` |
| **Process viewers** | **`ps_aux.txt`** (canonical table for **`ps_coherence`**), `ps_ef.txt` (reference; listing built from aux), `top_bn1.txt` (static header tail for **`top`**) |
| **Users / probes** | `id_pi.txt`, `id_cowrie.txt`, `wget_bad_flag.txt`, `service_status_all.txt`, `systemctl_running.txt`, `lsb_release_a.txt`, `hostnamectl.txt` |
| **Errors / edge** | `insmod_err.txt`, `make_kmodules_err.txt`, `cat_shadow_err.txt`, `cat_sudoers_err.txt`, `cat_enoent.txt`, `ls_enoent.txt`, `last_notfound.txt`, `lastlog_notfound.txt` |
| **`w` / sessions** | `w_decoy_sessions.txt` (decoy lines for **`w`** when faking uptime) |
| **Legacy / misc** | `last.txt`, `lastlog.txt`, `apt_moo.txt` — usage depends on **`rpi_ground`** branches |

---

## 8. Honeyfs (emulated filesystem overlay)

**Root:** **`honeyfs/`** — paths here appear under **`/`** in the guest shell (merged with **`fs.pickle`**).

| Area | Introduced | Purpose |
|------|------------|---------|
| **`honeyfs/etc/*`** | **v0.1.0** (refreshed **v0.2.0**) | **`issue`**, **`hostname`**, **`hosts`**, **`passwd`**, **`group`**, **`shadow`**, **`os-release`** (real file, not broken symlink), **`motd`**, etc. |
| **`honeyfs/proc/*`** | **v0.1.0** (**v0.2.0** sync) | Snapshots: **`cpuinfo`**, **`meminfo`**, **`modules`**, **`mounts`**, **`net/arp`**, etc. **`cat /proc/uptime`** may still be **dynamic** via **`Command_cat_gt`** when configured. |
| **`honeyfs/sys/.../model`** | **v0.1.0** | Device tree model string path (if present in tree). |
| **`honeyfs/home/`, `opt/`, `root/`** | **v0.2.0** | Lab-style trees for richer interaction; **audit before any public repo**. |
| **`honeyfs/var/log/*`** | Varies | Optional decoy logs (e.g. nginx, auth). |

---

## 9. Virtual filesystem pickle

| Path | Introduced | Purpose |
|------|------------|---------|
| **`src/cowrie/data/fs.pickle`** | **v0.2.0** (rebuilt when overlays change) | Cowrie’s pickled VFS; must stay **consistent** with **`honeyfs/`** layout. |

---

## 10. Large static text “binaries” (fork)

| Path | Introduced | Purpose |
|------|------------|---------|
| **`src/cowrie/data/txtcmds/bin/dmesg`** | **v0.1.0** | Pi-sized **`dmesg`** text served when the emulated command runs. |

---

## 11. Version tag → theme (quick reference)

| Tag | What landed (fork-relevant) |
|-----|-----------------------------|
| **v0.0.0** | Baseline: clone state **before** Pi 5 / ground-truth packaging documented here. |
| **v0.1.0** | **`ground_truth.py`**, **`pi5_debian13/`** captures, **`rpi_ground.py`**, **`uname` / `wget`** edits, **`commands/__init__.py`**, honeyfs **`/etc` + proc** fingerprint, **`dmesg`**, root **`README`** + personal changelog. |
| **v0.2.0** | Chunked **`ps`** output (SSH), **`os-release`** file fix, honeyfs + **`fs.pickle`** refresh, **`home` / `opt` / `root`** overlays. |
| **v0.3.0** | Anchor clock / fake uptime / **`display_timezone`**, **`get_shell_loadavg`**, **`utils`** time helpers, **`uptime` / `w` / `last`** coherence, **`ps_coherence.py`**, **`ps -ef`** / **`top`** from **`ps_aux`**, plain **`ps`** PIDs on protocol. |
| **v0.4.0** | Session-built **`ps aux`**, shared **`build_session_ps_rows`** for **`top`**, **`ps_aux_tail_noise_max`**, **`%MEM`/VSZ** formatter fix, **`.cursor/rules/scalpel-hackathon.mdc`**, **`RELEASE_NOTES_v0.4.0.md`**. |
| **v0.4.1** | **`RELEASE_NOTES_v0.4.1.md`** (this map) + README / personal changelog pointers. |

---

## 12. What this map does *not* enumerate

- **Thousands of upstream files** under **`src/cowrie/`** (SSH, telnet, plugins, tests, etc.) — treat as **Cowrie upstream** unless listed above.
- **Local-only paths** (`**cowrie-env/**`, **`var/log/**`, **`var/lib/**`**) — environment and telemetry, not the “fork contract.”
- **Secrets** — if **`honeyfs/`** or **`userdb`** contain real keys, that is **operational risk**, not something this document certifies as safe.

---

*For behavioral details of **`ps`** / **`top`** / **`w`** after v0.3.0, see **`RELEASE_NOTES_v0.4.0.md`** and **`PERSONAL_CHANGELOG_2026-04-23.md`**. For day-to-day knobs, start with **`README.md`**.
