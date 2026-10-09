# TEST A0-W — write/delete transfer preflight (ECC)

**Status:** `BLOCKED_BY_A0_R_RESULT`; `NOT_AUTHORIZED`; not executed. **Risk:** Tier 2, one temporary data file. A0-W does not authorize Test A.

## Entry gate

A0-W may be separately considered only after human review of A0-R establishes the exact existing destination and ordinary UID-2000 shell, expected API/ABI, no `/data` `noexec`, and observed `/system/bin/rm` metadata. A0-R must also establish enough destination metadata to verify exact absence and final cleanup. If any required fact is absent or inconsistent, do not start A0-W. A0-W always requires its own explicit authorization tied to a frozen exact sequence.

## Proposed sequence — not a runnable authorization

Use ADB sync/push to test the same transfer path intended for Test A. Before any future run, prepare one small inert plain-data marker on the host, verify exact bytes/hash and mode `0644`, and choose a unique exact filename offline. No executable bit, wildcard, shell redirection, `touch`, `mkdir`, chmod, or auto-chain is allowed.

1. Reconfirm the sole already-visible intended target and compare exact destination evidence with reviewed A0-R.
2. Confirm the exact marker path is absent with read-only `ls -l`; if present or ambiguous, stop.
3. `adb push` only the fixed marker to the one exact path.
4. Inspect that exact path using `ls -l`; optionally run the proven `/system/bin/md5` against that exact file and compare to host MD5 for transport consistency only.
5. Remove only that exact marker using the proven `/system/bin/rm` path.
6. Verify exact marker absence with read-only metadata inspection.

No marker creation, transfer, removal, or target command has occurred in R7E4. The literal path, bytes, ADB command syntax, command timeout, and recovery plan must be frozen in a later A0-W packet before separately asking for authorization. If transfer succeeds but exact removal cannot be established, stop and request a separately reviewed recovery plan. Never broaden cleanup.

## Audit boundary

| Operation | Reads | Writes | Process/privilege | Stop / rollback |
|---|---|---|---|---|
| Host preparation | host marker bytes/mode/hash | host-only marker | local user | wrong bytes/hash/mode stops |
| Exact absence check | destination entry | none | transient ordinary shell + `ls` | present/ambiguous stops |
| Push | exact source/destination | one non-executable 0644 marker | ADB sync service | any mismatch stops; no retry |
| Verify | exact marker metadata; optional MD5 | none | transient `ls`/`md5` | mismatch stops |
| Remove | exact marker path | unlink that file only | ordinary shell + proven `rm` | exact path only; no wildcard |
| Verify absence | exact marker metadata | none | transient `ls` | unresolved cleanup is an incident; no improvised cleanup |

A0-W cannot execute a program, chmod, kill a process, alter USB role, change system properties, or proceed to Test A. A0-W remains `BLOCKED_BY_A0_R_RESULT` and `NOT_AUTHORIZED`.
