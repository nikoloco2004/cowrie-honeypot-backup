# Release v0.4.5 — LLM removal, live `meminfo`, MOTD / last-login, Pi handoff

This tag snapshots the **Raspberry Pi 5 / Debian 13 (trixie)** honeypot fork for **lab-style medium interaction**: emulated shell + filesystem + optional **ground truth** captured from a real Pi, **without** the experimental **LLM** backend or hybrid “unknown command → model” path.

**Repository:** `https://github.com/nikoloco2004/cowrie-honeypot-backup`  
**Tag:** `v0.4.5`  
**Previous fork tag:** `v0.4.4` (LLM + Ollama-oriented config; see “Migration” below).

---

## Executive summary

| Area | What changed |
|------|----------------|
| **LLM** | Entire `src/cowrie/llm/` tree **removed**; `backend = llm` no longer supported. `cowrie_plugin` and docs updated. |
| **`/proc/meminfo`** | `cat` / ground-truth `cat` read **honeyfs on disk** after `memupdate.update()` so values are not stuck in pickle `A_CONTENTS`. |
| **MOTD / last login** | Synthetic **“Last login: … from &lt;ip&gt;”** after Debian disclaimer, **immediately above the shell prompt**; IP from `[honeypot] fake_addr` or real client. |
| **Config** | **`[llm]`** blocks removed from **`etc/cowrie.cfg`** and **`etc/cowrie.cfg.dist`**; **`backend`** comments corrected. |
| **Tooling** | **`src/cowrie/gen_lastlogin.py`**, **`src/cowrie/start_with_login.py`** (optional: refresh `honeyfs/etc/motd` body + `cowrie start`). |

---

## 1. LLM backend and hybrid removal

### Code removed

- `src/cowrie/llm/` — **deleted** (avatar, `LLMClient`, protocol, realm, server, session, telnet, `hybrid.py`).
- **`src/cowrie/shell/honeypot.py`** — no `maybe_schedule_hybrid_unknown`; unknown commands only get static **“command not found”**.
- **`src/twisted/plugins/cowrie_plugin.py`** — `import cowrie.llm.realm` removed. Portal selection only **`shell`** or **`proxy`**. `backend` values other than those raise **`ValueError`** with a short message.

### Configuration

- **`etc/cowrie.cfg`**, **`etc/cowrie.cfg.dist`**: **`[llm]`** section and related comments **removed** (Ollama host/model/hybrid settings from v0.4.4 must not remain for a consistent tree).
- **`docs/LLM.rst`**: **removed** (upstream doc is obsolete for this fork).
- **`docs/index.rst`**: **`LLM.rst`** dropped from the Sphinx toctree.

### Migration from v0.4.4

- Set **`[honeypot] backend = shell`** (already default here).
- Delete any local **`[llm]`** stanza if you still have overrides outside this repo.
- **Do not** expect **`cowrie`** to start with **`backend = llm`**; upgrade to this tag or keep a pre-0.4.5 checkout if you still need LLM (not recommended for Pi fidelity work).

### Security / ops

- No outbound **OpenAI-compatible** calls from the honeypot process for **shell** sessions.
- Output plugins (e.g. **`[openai]`** in `etc/cowrie.cfg`) are **unrelated** to the removed LLM shell; review those separately if you use them.

---

## 2. Live `/proc/meminfo` (custom_cache / memupdate)

### Problem

`HoneyPotFilesystem.file_contents()` can return **pickled inodes** with **`A_CONTENTS`**; **`memupdate`** rewrites **honeyfs** on disk, but **`cat`** could still show **stale** bytes from the pickle.

### Fix

- **`src/custom_cache/custom_mem/memupdate.py`**: **`read_fresh_honeyfs_bytes(virtual)`** reads **`honeyfs_meminfo_path()`** after **`update()`** for **`/proc/meminfo`**.
- **`src/cowrie/commands/cat.py`**: for paths in **`DYNAMIC_PATHS`**, if fresh bytes exist, use them; else fall back to **`file_contents()`**.
- **`src/cowrie/commands/rpi_ground.py`**: **`Command_cat_gt`**: same dynamic refresh + fresh read for **`/proc/meminfo`** when **`ground_truth = pi5_debian13`**.

### Configuration (`etc/cowrie.cfg`)

- **`[meminfo] mode`**: **`live`** (~0.12 s refresh, Pi-like drift) vs **`legacy`** (2 s throttle, older path behavior).  
  See comments in config and **`memupdate.py`**.

### Gitignored runtime files (unchanged from v0.4.4)

- **`.gitignore`**: `honeyfs/proc/meminfo`, `var/memstate.json` — **not** committed; recreated at runtime.

---

## 3. MOTD, last-login line, and helper scripts

### Behavior (`src/cowrie/shell/protocol.py`)

- **`HoneyPotInteractiveProtocol.connectionMade`**: calls **`HoneyPotBaseProtocol.connectionMade` first** so **`self.clientIP`** (and **`[honeypot] fake_addr`**) is set before the banner.
- **`displayMOTD()`**:
  1. Loads **`/etc/motd`** from the virtual FS (merged **honeyfs**).
  2. Strips a legacy leading **`Last login:`** line via **`strip_leading_last_login_line()`** in **`gen_lastlogin.py`**.
  3. Writes: **MOTD body** → **blank line** → **`Last login: &lt;time&gt; from &lt;ip&gt;`** → newline, then the normal **prompt** (e.g. `pi@webserver01:~$`).

### New modules

- **`src/cowrie/gen_lastlogin.py`** — **`generate(ip)`** (realistic time in the past), **`strip_leading_last_login_line`**.

### Optional starter

- **`src/cowrie/start_with_login.py`** — writes only the **Debian/MOTD body** to **`honeyfs/etc/motd`**, then runs **`cowrie start`** (requires **`cowrie` on `PATH`**, e.g. venv with **`pip install -e .`**). Last-login is **not** stored in the file; the **shell** injects it on connect.

---

## 4. File-level reference (for diffs and audits)

| Path | Note |
|------|------|
| `src/cowrie/llm/*` | Deleted |
| `docs/LLM.rst` | Deleted |
| `docs/index.rst` | No `LLM` toctree entry |
| `etc/cowrie.cfg` | No `[llm]`; `backend` comment; `[meminfo]` and Pi options as in tree |
| `etc/cowrie.cfg.dist` | Aligned: no `[llm]` in dist |
| `src/cowrie/commands/cat.py` | `DYNAMIC_PATHS` + `read_fresh_honeyfs_bytes` |
| `src/cowrie/commands/rpi_ground.py` | `DYNAMIC_PATHS` + `memupdate` for `Command_cat_gt` |
| `src/cowrie/shell/honeypot.py` | Hybrid import/call removed |
| `src/cowrie/shell/protocol.py` | `displayMOTD` + `connectionMade` order |
| `src/twisted/plugins/cowrie_plugin.py` | No LLM branch |
| `src/custom_cache/custom_mem/memupdate.py` | `read_fresh_honeyfs_bytes`, path/mode behavior |
| `src/cowrie/gen_lastlogin.py` | New |
| `src/cowrie/start_with_login.py` | New |

---

## 5. Raspberry Pi — redeploy checklist (future “back to the Pi”)

Use this when cloning **`v0.4.5`** on the original Pi or a fresh SD card.

1. **OS:** Debian 13 (trixie) on **Pi 5** matches the **ground-truth** profile **`pi5_debian13`** (see `src/cowrie/data/ground_truth/pi5_debian13/` and `rpi_ground.py`).

2. **Clone and branch**
   ```bash
   git clone https://github.com/nikoloco2004/cowrie-honeypot-backup.git
   cd cowrie-honeypot-backup
   git checkout v0.4.5
   ```

3. **Python venv (required path name is arbitrary; this matches docs)**
   ```bash
   python3 -m venv cowrie-env
   source cowrie-env/bin/activate
   pip install -U pip
   pip install -e .
   ```

4. **Config**
   - Start from **`etc/cowrie.cfg.dist`** or use the committed **`etc/cowrie.cfg`** as a template.
   - **SSH listen:** `[ssh] listen_endpoints` (e.g. `tcp:2222:interface=0.0.0.0`).
   - **Honeypot identity:** `[honeypot] hostname`, `fake_addr` (story IP for last-login / w / probes).
   - **Ground truth:** `[shell] ground_truth = pi5_debian13` (or `none` for stock Cowrie).
   - **meminfo:** `[meminfo] mode = live` or `legacy` as desired.
   - **Host keys / userdb:** `etc/ssh_host_*_key*`, `etc/userdb.txt` — **generate or copy**; do not commit private keys to a **public** repo.

5. **Run**
   ```bash
   source cowrie-env/bin/activate
   cowrie start
   # or: python -m cowrie.start_with_login   # refresh motd body + start
   ```
   - Logs: `var/log/cowrie/`
   - Runtime overlays: `honeyfs/proc/meminfo` (gitignored), `var/memstate.json` (gitignored)

6. **Firewall / port forward**
   - Expose only the honeypot port (e.g. **2222**); avoid forwarding to real SSH 22 on the same interface without understanding the risk.

7. **Version string**
   - **`src/cowrie/_version.py`** is generated (e.g. by **`setuptools-scm`**) and may be gitignored; after checkout + **`pip install -e .`**, the installed version reflects **git** state near **`v0.4.5`**.

---

## 6. Upstream Cowrie

This fork tracks **[cowrie/cowrie](https://github.com/cowrie/cowrie)** with local patches. Merging new upstream versions may **reintroduce** `src/cowrie/llm/`. Resolve **explicitly** if you need to stay LLM-free: drop upstream LLM or keep it unused with **`backend = shell`** and no hybrid (upstream may differ).

---

## 7. Authentication for Git (operators only)

- **Pushes** to `git@github.com:nikoloco2004/cowrie-honeypot-backup.git` require your **GitHub account** and either:
  - **SSH key** with access to the repo, or
  - **HTTPS + personal access token** (repo scope), or
  - **GitHub CLI** (`gh auth login`).

**This repository and these release notes do not store tokens or private keys.** Configure credentials only on the Pi or your workstation, not in committed files.

---

*Generated for tag **v0.4.5** — fork maintainers: keep this file with the tag for reproducible lab deployments.*
