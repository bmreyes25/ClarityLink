# R7E5C reviewed interpretation of prior A0-W stop

## Record handling

The private evidence at `build/r7e/a0w/evidence/20261010T182555Z-0de13f26` was read locally. Its raw metadata, command results, and selector files were not changed and are not included in Git. This document records only sanitized conclusions.

## Historical result retained

The previous collector decision remains `A0W_STOP_CONDITION`. The run pushed the single inert marker successfully. It observed a regular remote file, exact size 58, owner/group `shell:shell`, mode `0666`, and no executable permission. Exact `/system/bin/rm` succeeded and the exact path was verified absent. The collector did not run MD5 because it stopped on the then-required remote `0644` expectation. Therefore transport MD5 remains unproven for that run.

## Reviewed interpretation

`A0W_STOP_CAUSE_EXPECTATION_MISMATCH_LEGACY_ADB_MODE_SEMANTICS`

Pinned AOSP Android 4.2.2_r1.2 `file_sync_service.c` transforms the incoming mode by first propagating owner bits to group and then, using the updated result, propagating group bits to other. Thus host `0644` predicts remote `0666`. The Honda observation matches that documented behavior; this does not prove the Honda daemon's binary identity or lack of vendor changes.

The transfer and cleanup path was observed: `TRANSFER_AND_CLEANUP_PATH_OBSERVED`. Full acceptance remains `A0W_FULL_ACCEPTANCE_NOT_YET_CLOSED` because MD5 was not run. `NO_TARGET_CHMOD_REQUIRED`. The revised A0-WR package addresses the expectation by using host mode `0444`, which remains `0444` under the reviewed transform, and always attempting MD5 after a push attempt.
