# R7E7C Test A directory metadata review — 2026-10-11

## Decision

The prior Test A run stopped at the parent-directory metadata gate. Its private failure record confirms `push_attempted: false`, `diagnostic_started: false`, and `process_state: NOT_STARTED`. R7E7B Test A authorization was consumed by that stopped attempt; no retry was authorized here.

The separately authorized R7E7C observation ran exactly two Honda ADB commands: one `adb devices` inventory and one exact `ls -ld /data/local/tmp` query against the confirmed target. Inventory returned one connected device. The metadata command returned status 0, empty stderr, and the sanitized stdout:

```text
drwxrwx--x shell    shell             2026-10-11 09:20 tmp\r\n
```

The exact raw stdout and command record are preserved in the ignored private evidence file `build/r7e7c-readonly-evidence/directory-metadata-20261012T011952Z.json` (directory mode 0700; file mode 0600). Raw target selector data is confined to that private evidence.

Historical A0-R and A0-WR raw outputs use the same Android legacy format: permission, owner, group, date/time, and basename `tmp`; there is no numeric size or full path. The collector had required both a numeric size field and `/data/local/tmp`, so it rejected valid output despite the directory still having the expected `drwxrwx--x` mode and `shell:shell` ownership. Root cause: collector parser format mismatch, not an observed directory permission/ownership change.

## Offline correction

The collector now accepts exactly one `ls -ld` output line with the required mode, `shell` owner, `shell` group, and final token either `tmp` or `/data/local/tmp`. It continues to reject wrong permissions, owner/group, basename/path, empty output, and multiple lines. The frozen manifest records this requirement. No diagnostic binary, remote path, process command, watchdog, cleanup policy, or Honda state was changed.

Regression coverage includes the observed CRLF legacy output, the prior numeric-size/full-path form, permission and ownership mismatches, wrong final name, extra output, and empty output. Focused collector fixtures: 58 passed.

## Identity and authorization

- Repository: `bmreyes25/ClarityLink`, PR #19
- Starting HEAD: `05ae27ae7405d37a476d9106d96e551b887629a0`
- Collector SHA-256: `3ab879b59bb5f56a742381e5429e2b469f9ae2f1aa11535e74cac107394ebfdc`
- Manifest version: `R7E7C-TEST-A-COMMAND-SET-3`
- Manifest SHA-256: `299f4423f716a9fc5c4d11d921e2c38fe3f75134a30db517762ef3daec7a339a`
- Artifact SHA-256: `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063` (unchanged)

These new identities supersede the prior R7E7A package identities for any future Test A authorization. Test A remains **NOT_AUTHORIZED** and **NOT_EXECUTED** under this package. R7E7C authorization is exhausted. Honda operations are complete: two read-only ADB commands, zero writes, zero push attempts, zero diagnostic executions, and no Test A retry.

ECC: independent reviewer unavailable; manual ECC-guided safety and package review performed. Exact-head full validation and hosted checks remain pending.
