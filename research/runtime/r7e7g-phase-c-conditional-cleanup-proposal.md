# R7E7G Phase C conditional cleanup proposal — draft, inactive

No Phase C cleanup is authorized. The offline simulation has no Honda effect. The current Honda file and process states remain unknown.

## Eligibility after a separate Phase R review

The reviewer must have current evidence for **all** of these conditions before proposing a new Phase C authorization:

1. Exact intended Honda target identity and exact prior path are confirmed.
2. Phase R found one regular file with expected `shell:shell`, mode `0555`, size 7904, exact basename, and matching MD5 `6137a693a77646aaf9a4cf0f351731d4`.
3. Current process safety is established by independent, separately reviewed evidence. Phase R contains no process query, so its file result alone cannot meet this condition. Stale PIDs and an assumed reboot cannot establish it.
4. No conflicting identity, transport anomaly, unexpected stock-state observation, or material safety concern remains.
5. The user gives a distinct, single-use Phase C authorization bound to a reviewed frozen command package and current operator conditions.

If any condition is absent, return `PHASE_C_NO_GO`. Obtain a separately reviewed read-only process inspection plan if that is needed; do not infer safety or delete the file. An unexpected file, symlink, directory, mismatched hash, ambiguous output, or changed path is a stop.

## Proposed scope after authorization

Revalidate all approved target, exact-path identity, file, and process-safety conditions immediately before the write. Then issue **one** exact-path `/system/bin/rm` for `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`, followed by **one** exact-path absence observation. A timeout or uncertain response stops; it does not justify another removal or a success claim. No wildcard, `rm -rf`, directory cleanup, `ps` sweep, signal, root, `su`, diagnostic execution, Test A, or Test B is included.

The offline decision simulation covers: already absent (zero cleanup), expected file with process state unknown (`PHASE_C_NO_GO`), unexpected file (stop), process safety unknown (stop), and a **simulated** separately authorized exact-path removal after all gates. It cannot supply the missing real Honda process evidence.

## Future Test A authorization template — inactive

Only after real recovery evidence is reviewed, the exact path is absent, current process/stock-state concerns are resolved, and the final Test A collector/manifest/artifact identities and full command plan are independently reviewed may a **new** single-use Test A authorization be requested. Phase R authorization does not carry into Phase C; Phase C authorization does not carry into Test A; Test A never authorizes Test B.
