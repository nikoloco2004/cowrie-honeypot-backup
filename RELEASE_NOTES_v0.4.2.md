# Release v0.4.2 — Sync local honeyfs, pickle, config, and `lsb_release` captures

This release **commits previously local-only** tree changes so the backup repo matches the working honeypot layout on the Pi.

## What was pending (now in Git)

| Area | Changes |
|------|---------|
| **`etc/cowrie.cfg`** | Current operator edits (e.g. `[honeypot]` hostname and any other local tuning). |
| **`honeyfs/etc/crontab`** | Decoy cron table (vegabase pipeline / backup stubs). |
| **`honeyfs/etc/os-release`** | Refreshed overlay vs prior commit. |
| **`honeyfs/sys/firmware/devicetree/base/model`** | Device-tree model string overlay. |
| **`honeyfs/home/priyas/.ssh/`**, **`honeyfs/home/ryanm/.ssh/`** | Decoy `authorized_keys` for lab users (same story as other honeyfs home trees — **audit if repo ever goes public**). |
| **`honeyfs/proc/device-tree/*`** | Decoy **`compatible`**, **`model`**, **`serial-number`** under proc-style paths for probes. |
| **`src/cowrie/data/fs.pickle`** | Regenerated/updated virtual FS to match the honeyfs layout. |
| **`lsb_release` ground truth** | **`lsb_release_a.stdout.txt`** and **`lsb_release_a.stderr.txt`** added under **`data/ground_truth/pi5_debian13/`** (where **`load_ground_line`** loads them). Previously they sat under **`commands/`** and were untracked — wrong package path. |

## What was intentionally dropped

- **Empty junk files** at repo root (`exit`, `mkdir`, `touch`, 0 bytes) — not committed; removed from disk.

## Security

This commit may include **placeholder SSH material** under **`honeyfs/`**. Treat the backup repo as **private** unless scrubbed.
