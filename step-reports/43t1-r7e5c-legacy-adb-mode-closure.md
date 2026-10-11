# R7E5C legacy Android ADB mode-semantics closure — 2026-10-11

## Decision

`R7E_A0WR_LEGACY_MODE_PACKAGE_READY`

Next: `READY_FOR_EXPLICIT_USER_A0WR_AUTHORIZATION`. A0-WR remains unauthorized and unexecuted. Test A remains unauthorized. This milestone was offline only; no Honda commands or ADB were run.

## Finding

Pinned Android 4.2.2_r1.2 sources show ADB sync sends host `st_mode`, masks it to `0777`, then sequentially propagates owner permission bits into group and the updated group bits into other. `adb_main` clears adbd's umask with `umask(000)`. This exact `do_send` path contains no `/system`-specific `fs_config` override. Host 0644 therefore predicts 0666, matching the observed prior Honda mode. Behavioral match does not establish Honda binary identity.

## Previous A0-W disposition

Historical collector decision `A0W_STOP_CONDITION` is preserved. Push succeeded; remote regular file, size 58, `shell:shell`, non-executable mode 0666 observed; exact cleanup succeeded and absence confirmed. MD5 was not run. Reviewed cause: `A0W_STOP_CAUSE_EXPECTATION_MISMATCH_LEGACY_ADB_MODE_SEMANTICS`. Transfer and cleanup path observed, but `A0W_FULL_ACCEPTANCE_NOT_YET_CLOSED`. No target chmod is required. Raw private evidence remains local and unchanged.

## Revised package

A new collector and manifest freeze one unique-path A0-WR inert-marker lifecycle. Marker is 59 bytes, host mode 0444, predicted remote mode 0444, SHA-256 `3f84d1ff7d301409d5bebfba84b242ff8f0df20e2928a9fdc91687b40c573b9d`, MD5 `6cac328b32dad06f736d6a7ab78a20c8`; remote path `/data/local/tmp/claritylink_a0wr_r7e5c_5d73b2c42a7e19f0.probe`. The package requires exact mode, metadata, MD5, exact cleanup and absence; zero retries/fallbacks; exclusive ADB window; no chmod or auto-chain. Full binding is in the authorization packet and manifest.

Future Test A staging policy is an ignored copy with canonical artifact bytes and hash unchanged, local/expected remote mode 0555. This is planning only.

## Verification

Host-only verification: 973 passed, 15 skipped; 32 focused A0-WR fixtures passed; 3 self-locator smoke tests passed; simulator checks, repository health, and `git diff --check` passed. Hosted exact-head Offline CI and CodeQL are reported after publication. The fixtures include all six transform examples, previous observed 0666 classification, revised marker/mode checks, missing/symlinked/modified marker gates, invalid inventory and destination gates, MD5 outcomes, cleanup/absence failures, authorization default, dry run with zero ADB calls, and no Test A chain.
