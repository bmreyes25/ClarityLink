# TEST A0 — target environment preflight / A0-W (ECC)

**Status:** `BLOCKED_BY_A0_R_RESULT`; not authorized, not executed. **Risk:** Tier 2, narrowly bounded temporary write/delete. Separate authorization required after A0-R review. A0-W does not authorize Test A.

## Objective

If A0-R confirms the path and ordinary-shell context are suitable but write/delete remain unknown, test only whether ordinary shell can create, inspect, and delete one unique inert non-executable marker in the selected path. Do not run any executable, chmod, binary transfer, package install, display, listener, or service action.

## Gate and naming

A0-W remains `BLOCKED_BY_A0_R_RESULT` and requires separate Tier 2 authorization. It becomes relevant for review only when actual reviewed A0-R evidence reports the candidate destination present, observes UID-2000 ordinary shell and the expected platform, identifies no `/data` `noexec` blocker, and still leaves write/delete unproven. A missing/mismatched destination, elevated/unknown shell, platform mismatch, `noexec`, ambiguous target, command failure, or stop condition does not justify progressing to A0-W. Even a favorable A0-R result never authorizes A0-W automatically.

Select destination only from reviewed A0-R result. Do not default to `/data/local/tmp` if absent/different. The future exact path is `DESTINATION_FROM_APPROVED_A0_RESULT/claritylink_a0_<approved_nonce>.probe`. Nonce must be precomputed offline and unique; no runtime timestamp/shell expansion. Check exact path absence before create; if it exists, STOP. Commands below are design patterns, not runnable approval; final literal sequence is produced only after A0-R and separate A0-W authorization.

## Proposed minimum operation (NOT EXECUTED)

Prefer a single bounded shell builtin/known tool with fixed bytes, but no target write command is approved in this document. Final review must pin the payload bytes/hash, exact command behavior on API17, and exact path. Create exactly one marker, write a small known inert payload, read back/hash if a proven tool exists, inspect owner/mode, remove only exact marker, verify absence. No wildcard, recursive removal, chmod, execute bit, or fallback.

## Per-command audit template

| Stage | Reads | Writes | Path/bytes | Process/privilege | Expected result | Failure/rollback |
|---|---|---|---|---|---|---|
| Check absent | Exact marker metadata | None | Exact literal path | ordinary shell | absent | if present/malformed: stop |
| Create/write | Path parent metadata | One new marker; fixed small payload (size/hash to be pinned) | exact marker only | ordinary shell, one shell/tool process | success; file exact | stop; cleanup only if exact created path is verified |
| Verify | marker bytes/metadata | None | exact marker | ordinary shell | size/content/owner/mode recorded | stop on mismatch |
| Delete | exact marker | unlink exact marker only | exact literal path | ordinary shell | success | stop; do not wildcard or broaden |
| Verify absence | exact path metadata | None | exact marker | ordinary shell | absent | rollback unresolved; stop and request separate recovery plan |

Any command with uncertain side effects is rejected. No A0-W authorization is requested until A0-R results make its necessity and literal command semantics reviewable.
