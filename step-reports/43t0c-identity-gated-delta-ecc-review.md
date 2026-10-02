# Step 43T0-C — identity-gated delta dry run and ECC re-review

**Decision: `43T0_DELTA_ECC_GO` for the exact observational procedure below, in a separately initiated milestone only.** Starting HEAD `fb198013e0601c2b8a9b7c1c9157df7568dcc4c4` on clean `main`. `HONDA_CONTACTED = NO`; `ADB_USED = NO`; `TARGET_WRITES = 0`. The dry-run-only tool has no live execution path. No Honda, ADB, Type111, listener, runtime attachment, or 43T0-D/43T1 action occurred here. GO approves the procedure, not an implementation or a car session in this milestone.

## Evidence and ECC review

Reviewed `NEXT_ACTION.md`, `PROJECT_STATE.md`, `EVIDENCE_INDEX.md`, the [40E report](40e-readonly-runtime-preflight.md), [43T0 preflight](43t0-ecc-preflight-review.md), [43T0-A](43t0a-40e-network-evidence-reanalysis.md), [43T0-B](43t0b-exact-delta-ecc-review.md), and the [historical dry run](../tools/step43t0a_delta_dry_run.py). ECC evidence-first and security-review guidance was applied to command necessity, exact identity comparison, endpoint handling, dry-run inability to execute, privacy, failure and stop policy, and final decision. No independent external ECC reviewer capability was available; this is the documented ECC-method review, not an assertion of independent sign-off.

The trusted 40E host-only preflight files were read offline. Their artifact checksums are in the previously verified 40E manifest. The corrected [43T0-C dry run](../tools/step43t0c_identity_delta_dry_run.py) stores the five exact property expectations and SHA-256 of the **complete normalized** 40E `/proc/version` and `id` lines. Normalization removes only trailing CR/LF. This avoids committing the full build line or shell group list and does not weaken comparison to a substring. Static tests confirm the constants match the local 40E reference. 40E is real Honda/stock CarPlay without Type111; 43P is Mac/iPhone/PlayPort without Honda. Global 40E socket rows still do not prove `jmcs` ownership or new listener reachability.

## `43T0_DELTA_APPROVED_PLAN`

### 1. Preconditions, current target, and serial

The human must confirm: **“This is the parked Honda head unit intended for the test.”** It is normally powered; the Mac uses only the already established ADB-over-Wi-Fi route; the iPhone CarPlay cable is disconnected for baseline. Human confirmation supplements technical matching and is not cryptographic physical-unit proof.

The future host enumerates once with literal argv `["adb", "devices"]`. Require exactly one intended target in `device` state. Zero, multiple, `offline`, `unauthorized`, or any other state is `AMBIGUOUS_ADB_TARGET` and STOP. Never auto-select a second device or connect/scan a new endpoint. The current endpoint must equal the host-private historical 40E endpoint **as an additional fail-closed signal**, but equality alone is not identity proof. `CURRENT_ENDPOINT_DIFFERS_FROM_40E` means STOP even if other values appear to match; there is no override in this plan. The historical endpoint/serial is not printed in committed evidence or loaded into the new dry-run output. The dry run uses `<validated-current-target>` as a placeholder.

### 2. Identity gate before network reads

On the one enumerated current endpoint, execute these exact argv arrays in order, with no full `getprop` dump or device-ID property:

| Order | Target command after `adb -s <current-target> shell` | Exact expected result |
|---:|---|---|
| 1 | `id` | `uid=2000(shell) gid=2000(shell)` prefix **and** exact normalized 40E shell-identity SHA-256, including the historical group list. Root or changed groups stop. |
| 2 | `cat /proc/version` | Exact normalized 40E full-line SHA-256; this encompasses Linux `3.1.10+` and the preserved build fingerprint. No prefix-only match. |
| 3 | `getprop ro.build.version.release` | `4.2.2` |
| 4 | `getprop ro.build.version.sdk` | `17` |
| 5 | `getprop ro.product.device` | `vcm30t30a` |
| 6 | `getprop ro.product.board` | `Andromeda` |
| 7 | `getprop ro.hardware` | `vcm30t30` |

The state begins `IDENTITY_NOT_CHECKED`. Missing human confirmation, ambiguous target, missing result, or uncertain read produces `IDENTITY_INCOMPLETE`. A complete but nonmatching endpoint, privilege, kernel, or property produces `IDENTITY_MISMATCH`. Only all exact matches produce `IDENTITY_MATCH`. **Only `IDENTITY_MATCH` permits the first `/proc/net/*` read or `ifconfig`; no partial mode or manual override.** The pure gate model in the dry-run module enforces this when releasing network argv. Current endpoint selection and live read execution are not implemented here.

Check identity once before baseline. If ADB disconnects, reconnects, changes endpoint, or becomes unstable at any point, STOP and retain partial host evidence. Do not resume the same run or skip the gate. A separately initiated fresh run would repeat enumeration, human confirmation and all seven identity reads before any network read.

### 3. Three network phases and exact order

Keep **baseline → stock CarPlay connected → post-disconnect**. In each phase, with the same verified endpoint and no transport break, use only:

```text
["adb", "-s", "<validated-current-target>", "shell", "cat", "/proc/net/dev"]
["adb", "-s", "<validated-current-target>", "shell", "cat", "/proc/net/route"]
["adb", "-s", "<validated-current-target>", "shell", "cat", "/proc/net/ipv6_route"]
["adb", "-s", "<validated-current-target>", "shell", "cat", "/proc/net/if_inet6"]
["adb", "-s", "<validated-current-target>", "shell", "ifconfig"]
```

That is exactly **15 network reads**. `ifconfig` has **zero arguments**. The preserved firmware has a toolbox symlink, but current availability and output are unobserved; if unavailable, failed, malformed, or apparently requesting/configuring an interface, `STOP_AND_RETURN_PARTIAL`. No `ip`, `netcfg`, BusyBox, extra arguments, or other fallback. Each proc path is literal; if absent or unreadable, stop with partial evidence. Do not repeat socket tables, `jmcs` maps/FD, binary pulls, or broad proc reads.

After baseline, the user connects normal wired CarPlay and confirms center CarPlay, audio and stock cluster are normal before connected reads. Then the user disconnects normally, allows stock state to return, and confirms center system, audio and cluster before the final reads. No extra snapshots.

### 4. Bounds, host output, and result classes

For every **future** read: direct argv with `shell=False`; no host shell or dynamic target shell string; **5-second timeout** and **64-KiB combined stdout/stderr cap**. These are fail-closed bounds, not proof every new proc output fits. Never silently truncate. Use a fixed command table, no arbitrary command input, no target redirection/temp file, no target write, and no privilege path. An executable collector, if later authorized, must be separate from this dry-run-only module and match this plan exactly before use.

Raw output goes only to a mode-0700 owner-only Mac directory outside Git, with `manifest.json`, `identity/{id,proc-version,release,sdk,device,board,hardware}.raw`, and `<phase>/{net-dev,net-route,ipv6-route,if-inet6,ifconfig}.raw`. The host manifest records UTC start/end, phase, exact argv, result class, size and SHA-256. It is host-private and never auto-uploaded. The dry run only **prints** these destinations; it creates none.

Classify `SUCCESS`, `COMMAND_UNAVAILABLE`, `PERMISSION_DENIED`, `TIMEOUT`, `OUTPUT_LIMIT_EXCEEDED`, `UNEXPECTED_FORMAT`, `ADB_TRANSPORT_FAILURE`, `IDENTITY_MISMATCH`, `IDENTITY_INCOMPLETE`, `AMBIGUOUS_ADB_TARGET`, or `UNEXPECTED_PRIVILEGE`. Any non-success means STOP and return bounded partial host evidence. No retries through root, alternate utilities, or in-car troubleshooting. On ambiguous Android shell status, classify as uncertain and stop.

### 5. Privacy, parsing, and stop boundary

Commit only derived relevant interface name, family, Honda local address when necessary for bind design, IPv6 scope, route/interface association, and before/connected/after relationship. Redact MACs, unrelated IPs and gateways, Wi-Fi data, device serial, credentials, peers, and unrelated interfaces. Parse later on the Mac with deterministic sanitized fixtures; `/proc/net/route` requires little-endian IPv4 decoding, and `/proc/net/ipv6_route` fields must be validated against the exact format before interpretation. No additional target commands for parsing.

Stop on target ambiguity or mismatch, absent human confirmation, UID/root/group mismatch, kernel/property mismatch, missing identity value, transport change, unavailable/denied/timed-out/oversized/malformed read, unexpected `ifconfig` behavior, proposed argv deviation, or abnormal center CarPlay, audio, or stock cluster. Prohibited operations remain the [43T0 ECC denylist](43t0-ecc-preflight-review.md): no `su`, root, install, mount, network/configuration change, process control, target file write, `adb pull/push`, probe, listener, packet capture, Type111, `jmcs` modification, or runtime attachment.

### 6. Evidence and reversibility limits

G11-A becomes `YES_OBSERVED` only with a directly identified relevant interface. G11-B requires a Honda local address directly mapped to it. G11-C may become `IPv4`, `IPv6`, or `DUAL` only from phase-correlated evidence. G11-D requires direct route/interface support. G11-E remains `NO / READ_BLOCKED_WITHOUT_PRIVILEGE`; G11-F remains `NO`. No Type111 acceptance, bind success, listener reachability, security, media, CoreFoundation bridge, or cluster rendering follows from this observational plan.

43T0-C performed no target action and needs no Honda rollback. If a later approved session completes, the possible claim is `NO_INTENTIONAL_MUTATION_OCCURRED`, not `ZERO_PHYSICAL_STATE_CHANGE`; normal ADB, CarPlay, proc, log, counter, and filesystem bookkeeping can change ephemeral state.

## ECC final decision and next milestone

The 43T0-B blocker is corrected in the dry-run plan: current enumeration and human confirmation precede seven exact identity reads; the old serial is an additional comparison only; endpoint difference and reconnect stop; every nonmatch blocks network argv. The network set, three phases, output bounds, no-fallback policy and privacy boundary remain narrow. **`43T0_DELTA_ECC_GO` applies only to this canonical observational procedure.**

**Next milestone: separately initiate 43T0-D, a read-only Honda delta session under this plan, after reviewing any future executable collector against the canonical plan.** This report does not create or run that collector and does not start a car session. Runtime/deployment remains disabled.

## Offline verification

Focused tests use synthetic identity data and import the dry-run module without running its CLI or any ADB command. They cover fixed ordered argv, no process/socket imports, 15 network records, exact match, root/group/kernel/property mismatch, unavailable/ambiguous endpoint, human confirmation, and fail-closed network release: **15 passed**. The local reference hashes matched the host-only 40E bytes. The configured offline suite passed **415 tests, 3 skipped**, plus self-locator and simulator checks. Relative links and scoped redaction scan passed; staged `git diff --check` and hosted Offline CI are final gates. No raw capture is to be staged.
