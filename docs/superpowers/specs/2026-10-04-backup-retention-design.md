# Backups: full, kept for seven years, failures reported

**Date:** 2026-10-04
**Status:** Approved for implementation. The owner asked for "a proper back up system" and then "i want full backups on icloud drive".

## Problem

`scripts/reports/cc_backup.py` writes an encrypted full backup of `~/lcs-private` to iCloud Drive every night at 02:30 (about 13 MB). It has three gaps for company records:

1. **Only 14 days are kept.** Company accounting records must be kept for six years after the end of the period they cover. A mistake noticed after a fortnight can't be recovered from the backups.
2. **The Command Centre's cache is left out,** so a backup isn't quite a full copy of the private records. The cache holds the Books, calendar, drafts and marketing snapshots, about 28 KB.
3. **A failed run is silent.** The run writes to its error log (one ended "InterruptedError"), and nothing tells the owner. The Health page only notices once 36 hours have passed without a backup.

## Design

- **Retention** (`kept`, used by `prune`). It keeps:
  - every backup of the last 14 days;
  - the last backup of each ISO week for 8 weeks (the current week counts as one);
  - the last backup of each calendar month for 84 months (7 years);
  - the newest backup, always.

  At about 13 MB each, that is about 14 + 8 + 84 files, roughly 1.4 GB at most, on iCloud Drive. As before, only files with the exact backup name pattern are touched, never symlinks or other files.
- **Full backups.** Only the app's own copies of the public GitHub code (`command-centre/mirror.git` and `command-centre/runs`) and the backups folder are left out. The cache is now included.
- **Failures.**
  - `run`, as the LaunchAgent and "Back up now" call it, adds `error` and `failed_at` to `backup-state.json` on failure. The last good backup's fields stay, so the 36-hour check still measures from it.
  - It posts a macOS notification ("LCS backup failed"); `LCS_NO_NOTIFY` silences it, as the tests do.
  - A successful run writes a fresh state, clearing the error.
  - `sources.backup_status` reports the error only when it is newer than the last good backup. The Health check, the Health page and the Today attention list then show "the last run failed (…)".
- **Wording.** The "Back up now" description, the run's output line and the Health page note state the new retention.

## Out of scope

- A second location (an external drive or another cloud). The owner chose iCloud Drive alone.
- Automatic restore tests: the private key lives only in the password manager, so `verify` stays a manual step.

## Testing

`tests/test_cc_backup.py`:
- `kept` over a month of nightly backups plus older ones: nightly, weekly, the monthly edge at 84 months, and the newest always;
- `prune` touching only its own files;
- the cache in the archive;
- a failed run keeping the last good backup's fields, recording the error and notifying;
- Health and Today showing the failure, and a later success clearing it;
- the action's wording.
