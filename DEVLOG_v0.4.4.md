# Devlog — v0.4.4 (local LLM, git ignore overlays, release docs)

Narrative for **developers and operators** working from this fork. Complements **`RELEASE_NOTES_v0.4.4.md`** and the git tag.

---

## 1. Context

- **Fork goal:** Honeypot on **Raspberry Pi 5** / **Debian 13** with optional **ground-truth** shell fidelity (prior tags **`v0.4.0`–`v0.4.3`**).
- **This increment:** Turn on Cowrie’s **documented** LLM backend, wire it to a **local** OpenAI-compatible server (**Ollama** per **`docs/LLM.rst`**), and stop committing volatile **`proc`**/runtime paths.

---

## 2. Upstream source of truth (no custom protocol)

- **File:** `docs/LLM.rst` in this repository (from upstream Cowrie).
- **Mechanism:** `src/cowrie/llm/llm.py` — **`LLMClient`** reads **`[llm]`** from `CowrieConfig`, **POSTs JSON** to `{host}{path}` with **Chat Completions**-shaped body, parses **`choices[0].message.content`**.
- **Local server:** The doc’s example is **`host = http://localhost:11434`**, **`path = /v1/chat/completions`**. Ollama exposes that route in **OpenAI compatibility** mode. We use **`127.0.0.1`** in **`etc/cowrie.cfg`** to avoid DNS/`localhost` resolution surprises on minimal systems.

**Not invented here:** No alternate HTTP client, no extra proxy layer in the fork for this tag—only **configuration** and **docs**.

---

## 3. `etc/cowrie.cfg` — concrete keys

| Key | Rationale |
|-----|-----------|
| `backend = llm` | Activates `src/cowrie/llm/` protocol path instead of default shell. |
| `api_key` | Cowrie **always** sets **`Authorization: Bearer`**. **OpenAI** needs a real key. **Ollama** on loopback usually accepts a dummy string. |
| `model` | Must match the server: for Ollama, use the tag from **`ollama list`** (e.g. **`llama3.2:1b`**, not the generic **`gpt-4o-mini`** default in code). |
| `host` / `path` | Must match a server that returns OpenAI-style **`choices`/`message`/`content`**. |

**Operational note:** If Cowrie logs **`WARNING: No LLM API key configured`**, the key is empty; for Ollama a non-empty placeholder is enough to silence the warning and satisfy header construction.

---

## 4. Git: `honeyfs/proc/meminfo` and `var/memstate.json`

- **`honeyfs/proc/meminfo`:** **Mutable** on the real Pi as Cowrie or tests run; if tracked, every session produces noisy diffs. **Resolution:** add to **`.gitignore`**, then **`git rm --cached honeyfs/proc/meminfo`** so the blob leaves the **index** but the path can still exist in **`contents_path`**.  
- **`var/memstate.json`:** Runtime/session file under **`state_path`**; should not be versioned. **`.gitignore`** line added.

**Clone vs Pi:** A fresh **clone** will not create **`meminfo`** until runtime/honeyfs sync; the honeypot may generate or expect an overlay file—**ignored** means Git does not manage it.

---

## 5. Validation performed (Ollama)

- **`ollama list`** — confirm **`model` in `cowrie.cfg`** names an installed model.
- **`curl -sS http://127.0.0.1:11434/v1/chat/completions`** with **`Content-Type: application/json`**, **`Authorization: Bearer ollama`**, and minimal **`messages`** array — expect **`200`** and JSON with **`choices[0].message.content`**.

**Cowrie path:** On login, any command in LLM mode triggers **`LLMClient.get_response()`**; failures log **`LLM API error (status …)`** with body snippet—use **`[llm] debug = true`** for full request/response JSON in **`var/log/cowrie/cowrie.log`** (see **`docs/LLM.rst`**, Debugging).

---

## 6. Rollback

- Set **`[honeypot] backend = shell`**, save **`etc/cowrie.cfg`**, restart **Cowrie** (`cowrie stop` / `cowrie start` or systemd).
- Prior behaviour (ground truth, **`rpi_ground`**, **`fs.pickle`**, etc.) is unchanged when **`backend = shell`**.

---

## 7. Tag and release discipline

- **Tag:** `v0.4.4` (annotated), **after** the commit that includes **`RELEASE_NOTES_v0.4.4.md`**, **`DEVLOG_v0.4.4.md`**, and version bumps in **`README`**, **`CHANGELOG.rst`**, **`PERSONAL_CHANGELOG_2026-04-23.md`**.
- **Push:** `git push origin main` and `git push origin v0.4.4` so the backup remote matches the tag.
- **GitHub UI:** Create a **Release** from tag **`v0.4.4`** and paste **`RELEASE_NOTES_v0.4.4.md`** (or a subset) as the description.

---

## 8. Files touched in the documentation commit (expected)

- `README.md` — “This document’s release”, version table, changelog blurb, restore/checkout hint.
- `CHANGELOG.rst` — new **Release 0.4.4 (fork)** section at the top of the fork’s release notes.
- `PERSONAL_CHANGELOG_2026-04-23.md` — postscript for **v0.4.4**.
- `RELEASE_NOTES_v0.4.4.md`, `DEVLOG_v0.4.4.md` — this content.

*End of devlog v0.4.4.*
