# CL-HONDA-ROOT-ACCESS-V2

**Question →** Under what measured conditions can the archived SuperSU facility
be used for one tightly bounded receiver-observation session without treating
its executable mode as safe or changing the receiver?

**Method →** Preserve the October root campaign and add a separate V2 policy,
source-locked profile, one-use owner authorization, legacy-path integrity
assessment, and fixed-operation runner. No Honda or ADB session was run for
this report.

## Baseline and policy correction

The active public baseline is fetched `origin/main` at `f32f87d3f5737f3fda8d50e06ab9663c4087a810`.
The original root campaign is PR [#119](https://github.com/bmreyes25/ClarityLink/pull/119),
head `3d237a60a54557f7a1420eab7b04cc5bd83cbeec`, still open and conflicting
with current `main`. Its old validator rejects writable group/other bits, so
it rejects the archived `06777` mode; its runner is hard-disabled. The preserved
record remains unchanged: Chainfire SuperSU 2.77-family at
`/system/xbin/su`, SHA-256
`d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`, owner
`root:root`, archived mode `06777`, and historical successful root command.
Potential prompt, daemon, policy, request and log writes remain real risks.

V2 does not weaken the mode check. It records `06777` as HIGH residual risk
and permits only an exact owner-approved session if the current hash, size,
root ownership, regular-file type, non-symlink path chain, read-only covering
mount and root-owned non-writable parent directories match. Writable or
ambiguous mounts, overlay/bind uncertainty, changed path metadata, or any
unprivileged replacement route fail closed. A final SHA-256 check is the last
target read before each `su -c` action. This narrows replacement risk; it does
not prove race-free immutable execution or zero-write SuperSU behavior.

The current repository risk-level policy already distinguishes routine offline
work, controlled diagnostics and high-risk receiver/display changes. V2 makes
the controlled diagnostic criteria concrete. It leaves
`safeForHonda() == false`, `HONDA_TYPE111_NOT_PROVEN` and
`VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` unchanged. Existing C-P approvals and
source pins remain historical and cannot authorize this root session.

## V2 workflow

`tools/honda-readonly-preflight/root_access_v2.py` accepts only an exact ADB
endpoint and exact fixed operations. The draft helper leaves the endpoint,
expiry, risk acceptance and power state blank and starts every owner/readiness
field false. It writes mode 0600 in an existing owner-only directory and
performs no device I/O. A live invocation requires profile/source-lock
hashes, target properties, one fresh 128-bit run ID, exact scope, a 15-minute
expiry, `PARKED_ON_READY_ABSENT`, an explicit SuperSU side-effect acceptance,
and final interactive YES. YES is followed by source/authorization revalidation
and durable one-use ledger consumption before ADB. Replay, changed source,
expired authorization, wrong endpoint, or wrong target stops the run.

The three snapshots are disconnected baseline, owner-operated normal wired
CarPlay connected, and normal post-disconnect. They record root identity;
`jmcs` PID/start-time, all UID/GID slots, command line and executable link;
executable maps; process FD links; `/proc/net` TCP/UDP/Unix tables; `/proc/net/dev`;
Android display/window/SurfaceFlinger inventory; and activity service ownership
metadata. A private correlation summary joins exact `jmcs` socket FD inodes to
network table rows. A match demonstrates process ownership only; it does not
label an endpoint as control or media without phase evidence.

Limits are 15 minutes, 141 commands, 12 MiB combined output, 10 seconds and
2 MiB per command, and at most 192 `jmcs` FD rows. There is no retry, endpoint
fallback, device scan, `adb root`, custom helper, memory read, process attach,
packet capture, or arbitrary-shell argument. Raw records stay outside Git in
owner-only host storage. Timeouts preserve partial evidence and stop; no target
cleanup command is run. A remote command's termination after host-side ADB
timeout is not independently established, so timeout is a terminal failure.
Potential SuperSU daemon/request/log state is not deleted or reversed.

## Separate HondaHack UI observation

The [vehicle procedure](../docs/safety/vehicle-testing.md) separates this
root scope from a normal UI-only HondaHack experiment. That experiment needs no
root or ADB: enter factory Navigation; use existing HondaHack Start Casting;
exit and re-enter Navigation with normal controls; Stop Casting; verify factory
restoration. It preserves the current Level 2 qualified review requirement for
the Display 1 observation. It does not install ClarityLink or prove Type111
frame admission.

## Evidence and verification

Host tests verify `06777` risk classification, read-only versus writable mount,
symlink/path/ownership/hash/size checks, parent write-bit rejection, exact
target and authorization binding, expiry, missing risk acceptance, replay,
source tampering, command allowlisting, output/timeout stop behavior, and
private abort manifests. The exact 141-command budget is the sum of 24 target
identity reads, 16 SuperSU mount/path/mode/hash assessment reads, 86 elevated
invocation and immediately preceding digest reads, and 15 display/network
reads. A full fake-ADB run must exercise all three phases at exactly this
count; no real ADB process is used by the harness.

Android 4.2.2 AOSP `toolbox/ls.c` confirms that `-n` selects numeric long
output with mode, UID, GID, size, ISO timestamp and basename, without link
count. The root basename is empty. The parser accepts that exact form plus a
separately tested numeric link-count layout, and rejects unknown dates,
ambiguous columns, malformed mode/owner, unexpected names and symlinks. Source:
[Android 4.2.2 Toolbox `ls.c`](https://android.googlesource.com/platform/system/core/%2B/android-4.2.2_r1.2/toolbox/ls.c).

The earlier Offline CI collection failure was caused by the active campaign
source lock retaining the collector digest from commit `d16488b`, before commit
`26e58e4` changed the fixed `hash-jmcs` command to use the documented BusyBox
path. The lock is now updated to the actual current collector SHA-256; the old
digest remains in Git history and was not represented as the new digest. Any
approval bound to the previous source map is stale and cannot authorize this
source revision. The campaign itself, its profile, and its historical evidence
were not rewritten. V2 and comprehensive source locks are repinned to their
actual source contents.

Latest offline verification: full Honda suite **906 passed, 2 skipped, 19
subtests passed**; the focused runner/integrity/campaign set **178 passed**.
The comprehensive source-lock verifier reports all 33 pinned sources valid.
No raw Honda output has been collected.

**Observation →** The old campaign has an internal mode-policy conflict. A
versioned controlled path can evaluate the same archived binary without
mislabeling `06777` as safe, provided current filesystem protections make the
executable non-replaceable by unprivileged actors and the owner accepts the
remaining side effects.

**Conclusion →** Offline checks make V2 executable and fail-closed; they do not
authorize or establish the live session. The actual mount/path/process facts
remain to be observed.

**Next action →** The Honda owner reviews the exact V2 profile and source-lock
hashes, prepares and explicitly approves one private authorization, confirms
Park/parking brake/ON with READY absent and normal factory behavior, then starts
the runner manually. If any current integrity check fails or the transport is
unavailable in that state, stop without mode repair, remount, fallback, or
escalation. The first observation then selects whether a passive session trace
can expose SETUP ownership or whether a separately reviewed reversible runtime
diagnostic is needed.
