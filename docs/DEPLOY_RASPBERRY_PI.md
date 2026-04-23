# Deploying this Cowrie fork on a new Raspberry Pi

This document describes how to take **everything in this GitHub repository** and run it on **another Raspberry Pi** (or another Debian/arm64 host) from scratch. It is tailored to this fork:

- **Repository:** [nikoloco2004/cowrie-honeypot-backup](https://github.com/nikoloco2004/cowrie-honeypot-backup)
- **Extras in this fork:** Debian 13 / Pi-flavoured shell ground truth, `honeyfs` overlays, `fs.pickle`, and `etc/cowrie.cfg` tuned for a coherent emulated host (see `CHANGELOG.rst`).

Upstream Cowrie docs still apply for general concepts: [INSTALL.rst](https://github.com/cowrie/cowrie/blob/main/INSTALL.rst) and [docs.cowrie.org](https://docs.cowrie.org/).

---

## 1. What you need

| Item | Notes |
|------|--------|
| **Hardware** | Raspberry Pi (64-bit OS recommended; fork targets **aarch64** / Pi kernel strings in config). |
| **OS** | Raspberry Pi OS (Debian Bookworm or newer) or plain Debian arm64. |
| **Network** | The Pi must be reachable on the port you expose for SSH (default **2222**, or **22** if you redirect). |
| **Access** | SSH or console as a user with `sudo` for package install; a **dedicated `cowrie` user** is recommended to run the honeypot. |
| **Disk** | A few hundred MB for the repo + venv + logs; more if you keep many downloads/session logs. |

---

## 2. Prepare the Pi (system packages)

Install build and SSL dependencies (same family as upstream Cowrie):

```bash
sudo apt-get update
sudo apt-get install -y \
  git \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  libssl-dev \
  libffi-dev \
  build-essential \
  authbind
```

Optional but useful: `vim` or `nano`, `iptables` / `nftables` if you will redirect port 22.

---

## 3. Create a dedicated user (recommended)

Do **not** run Cowrie as root long term.

```bash
sudo adduser --disabled-password cowrie
sudo su - cowrie
```

All remaining steps in this guide assume you are **`cowrie`** (or you adjust paths accordingly).

---

## 4. Clone **this** fork (not upstream Cowrie)

From the `cowrie` user home (or `/opt` if you prefer a fixed path):

```bash
cd ~
git clone https://github.com/nikoloco2004/cowrie-honeypot-backup.git cowrie
cd cowrie
```

**Pin to a known release (recommended for repeatability):**

```bash
git fetch --tags
git checkout v0.4.3   # or: git checkout main
```

Using SSH instead of HTTPS:

```bash
git clone git@github.com:nikoloco2004/cowrie-honeypot-backup.git cowrie
```

---

## 5. Python virtual environment and install

Cowrie expects a venv named **`cowrie-env`** next to the repo (or you activate any venv before `cowrie start`).

```bash
cd ~/cowrie
python3 -m venv cowrie-env
source cowrie-env/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

This installs the `cowrie`, `playlog`, `fsctl`, etc. console scripts **into the venv**.

Verify:

```bash
which cowrie
cowrie --help
```

---

## 6. Configuration files that matter in **this** repo

Cowrie reads **`etc/cowrie.cfg.dist`** (defaults) and **`etc/cowrie.cfg`** (overrides). This fork **tracks** a customized `etc/cowrie.cfg` in Git so a fresh clone already has Pi-oriented settings.

After clone, review at least:

| Setting / file | Purpose |
|----------------|--------|
| `[honeypot] hostname` | Emulated hostname (e.g. `webserver01`). |
| `[honeypot] contents_path` | **`honeyfs`** — static file contents for `cat` etc. |
| `[honeypot] filesystem` | **`src/cowrie/data/fs.pickle`** — virtual FS metadata. |
| `[honeypot] data_path` | **`src/cowrie/data`**. |
| `[shell] ground_truth` | **`pi5_debian13`** enables Pi/Debian 13 ground-truth command output. |
| `[shell] ground_truth_id_as_pi` | Cosmetic `pi` identity for `id` / prompt when SSH is `root` (see comments in `cowrie.cfg`). |
| `etc/userdb.txt` | **Login/passwords** accepted by the honeypot (edit to taste). |

**Important:** Paths in `cowrie.cfg` are usually **relative to the repository root** (the directory that contains `etc/`, `honeyfs/`, `src/`). Always start Cowrie with **working directory = repo root** (see systemd example below).

---

## 7. SSH host keys (first-time setup)

If `etc/` has no host keys yet, generate them once (from repo root, venv active):

```bash
cd ~/cowrie
source cowrie-env/bin/activate
make keys
# or follow upstream docs if `make keys` is unavailable in your checkout
```

If your tree already contains `etc/ssh_host_*` keys in Git **do not** commit private keys to a **public** repo; this fork should only ship keys suitable for a **honeypot** (low trust). Prefer generating fresh keys on each new Pi.

---

## 8. Start Cowrie (foreground / manual)

From repository root:

```bash
cd ~/cowrie
source cowrie-env/bin/activate
cowrie start
```

Default SSH listen port is **2222** (see `[ssh] listen_endpoints` in `cowrie.cfg`).

Test from another machine:

```bash
ssh -p 2222 root@<PI_IP_ADDRESS>
```

---

## 9. Run on port 22 (optional, read carefully)

Real attackers often hit **22**. Moving **real** `sshd` off 22 and redirecting **22 → 2222** is common. This can **lock you out** if misconfigured.

Typical pattern:

1. Move real SSH to e.g. **22222** in `/etc/ssh/sshd_config`, reload `sshd`.
2. Apply **iptables** or **nftables** redirect **22 → 2222** (see `INSTALL.rst` in upstream).

Test from a **second** host, not from loopback, when validating firewall rules.

---

## 10. systemd (optional, production-like)

Upstream ships a **template** under `docs/systemd/etc/systemd/system/cowrie.service`. Adapt paths to your Pi, for example:

- `WorkingDirectory=/home/cowrie/cowrie`
- `User=cowrie` / `Group=cowrie`
- `ExecStart=/home/cowrie/cowrie/cowrie-env/bin/python /home/cowrie/cowrie/cowrie-env/bin/twistd --umask 0022 --nodaemon --pidfile= -l - cowrie`

Copy the unit to `/etc/systemd/system/`, run `sudo systemctl daemon-reload`, `sudo systemctl enable --now cowrie`.

Ensure `WorkingDirectory` is the **git checkout root** so relative `honeyfs`, `var/`, and `etc/` resolve correctly.

---

## 11. What gets created at runtime (not in Git)

These directories fill up on the Pi; they are usually **gitignored**:

- `var/log/cowrie/` — `cowrie.log`, JSON logs, etc.
- `var/lib/cowrie/tty/` — session transcripts
- `var/lib/cowrie/downloads/` — files pulled by attackers

Back them up if you care about evidence.

---

## 12. Updating from GitHub later

```bash
cd ~/cowrie
sudo systemctl stop cowrie   # if using systemd
source cowrie-env/bin/activate
git fetch origin
git checkout main            # or a release tag
git pull
python -m pip install -e .   # refresh deps if pyproject changed
sudo systemctl start cowrie
```

Resolve merge conflicts in **`etc/cowrie.cfg`** carefully; keep local secrets (`userdb`, keys) out of public commits.

---

## 13. Troubleshooting

| Symptom | Check |
|---------|--------|
| `cowrie: command not found` | `source cowrie-env/bin/activate` or use full path to venv `cowrie`. |
| Import / module errors | `pip install -e .` from repo root; Python **3.10+**. |
| Empty or wrong `cat` / OS identity | `ground_truth` value, `honeyfs/`, `contents_path`, and that cwd is repo root. |
| SSH closes on first command | See `CHANGELOG.rst` (recent fixes for `w`, `cat`, `lsb_release`, etc.); ensure you run an **updated** tag. |
| Permission denied on port 22 | Use **authbind**, **capabilities**, or **iptables** redirect to 2222 instead of binding as non-root. |

Logs: **`var/log/cowrie/cowrie.log`** (path from `[honeypot] log_path`).

---

## 14. Quick checklist for a **new** Pi

1. [ ] Install apt dependencies  
2. [ ] Create `cowrie` user  
3. [ ] `git clone` this fork → `~/cowrie`  
4. [ ] `git checkout` specific **tag**  
5. [ ] `python3 -m venv cowrie-env` → `pip install -e .`  
6. [ ] Generate or install **SSH host keys** under `etc/`  
7. [ ] Edit **`etc/userdb.txt`** and any local **`etc/cowrie.cfg`** overrides  
8. [ ] `cowrie start` from repo root (or systemd)  
9. [ ] `ssh -p 2222 ...` from another host  
10. [ ] Optional: port **22** redirect, firewall, log rotation  

---

## 15. Asking an assistant (e.g. Cursor) to do this later

You can paste:

> Install the **nikoloco2004/cowrie-honeypot-backup** repo on this Pi per **`docs/DEPLOY_RASPBERRY_PI.md`**: clone, venv, `pip install -e .`, keys, `userdb`, start service, verify SSH on port 2222.

Point the assistant at **this file** and the **tag** you want (e.g. `v0.4.3`).
