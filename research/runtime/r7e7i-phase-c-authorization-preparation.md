# R7E7I conditional Phase C authorization preparation — inactive

Phase R found the exact transferred file with expected mode, owner/group, size, and MD5. Its remote SHA-256 was not measured. Phase R did not inspect process state. Phase S is prepared offline but has not run. Therefore `PHASE_C_NO_GO` remains the current decision; this file is not permission to delete anything.

## Required gates before preparing a final frozen cleanup package

1. Fresh operator confirmation of stationary/safely parked vehicle, normal display/cluster/no unexpected warnings, intended already-connected Honda serial, stable transport, and exclusive ADB window.
2. Review the unchanged private Phase R evidence and reconfirm the exact prior path, regular-file type, `0555`, `shell:shell`, 7904 bytes, and MD5 `6137a693a77646aaf9a4cf0f351731d4` immediately before the write. The earlier MD5 check is a historical identity observation, not a guarantee that the path cannot change later.
3. Sufficient **current** process-safety basis. A Phase S later-boot result establishes only that the *previous* invocation terminated. Independently resolve any later-relaunch risk and any uncertainty about a current process mapping or executing the file. Do not infer safety from an empty `ps`, a process name, guessed or reused PIDs, display power, or an assumed reboot. If a broader process inspection is needed, review and authorize it separately.
4. No conflicting target/file identity, transport anomaly, stock-state concern, or material uncertainty. Any changed file/path or uncertain process state means `PHASE_C_NO_GO`.
5. Independently review and freeze the final exact cleanup collector, manifest, ordered command plan, timeout behavior, evidence schema, and hashes. Obtain a **new**, single-use Phase C user authorization bound to that package and the current operator conditions.

## Exact proposed write scope, only after all gates pass

Following the reviewed pre-write target/file/process revalidation, issue one and only one:

```text
adb -s <EXACT_CONFIRMED_HONDA_ADB_SERIAL> shell /system/bin/rm /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f
```

Then issue one exact-path absence verification:

```text
adb -s <EXACT_CONFIRMED_HONDA_ADB_SERIAL> shell ls -ld /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f
```

Accept only the previously reviewed exact `ENOENT` form as absence. A timeout or ambiguous response stops; it does not justify retrying `rm` or claiming cleanup. No wildcard, recursive deletion, root, `su`, signal, process kill, chmod, diagnostic launch, or automatic Test A is in this proposal. Linux unlink can remove the pathname while an open executable remains in use, so `rm` plus ENOENT never substitutes for process-safety evidence.

## Earliest Test A retry eligibility

After a separately authorized Phase C succeeds, independently review private evidence of exact-path absence and the current stock state, close any process/relaunch concerns, verify the unchanged ARMv7 artifact and R7E7F Test A package hashes, review the complete Test A command plan and unresolved API17 stress-test risk, then request a **new**, single-use Test A authorization. Test B remains separate. The operator need not return to the vehicle for this offline preparation; a later authorized Phase S inspection would require a parked vehicle session.
