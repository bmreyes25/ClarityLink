# ClarityLink Honda read-only preflight readiness — 2026-10-13

## Purpose and present authorization state

This document is a proposal for review only. **No Honda was contacted. No Honda ADB command was run. No diagnostic was launched, removed, or cleaned up. No vehicle was rebooted or modified. No phone was connected.** None of the statuses below authorizes execution automatically.

Repository `bmreyes25/ClarityLink`, PR #19, baseline HEAD `6cc9bc263e4e7f0974ababddc0466f5d3b0d77cd`. This proposal uses the prior ECC audit at [claritylink-pre-vehicle-ecc-audit.md](claritylink-pre-vehicle-ecc-audit.md), the committed static research cited below, and the historical recovery reports. It refines the prior audit's broad preflight wording: only one ordinary user-facing identity observation is suitable to request as a first, separately authorized session. All ADB work remains blocked by unresolved recovery/process uncertainty and must have its own later authorization.

## Readiness summary

| Gate | Current result | Consequence |
|---|---|---|
| Offline plan review | **GO_FOR_PREFLIGHT_PLAN_REVIEW** | This packet can be reviewed. It authorizes no vehicle contact. |
| One passive/user-facing identity observation | **GO_FOR_SEPARATELY_AUTHORIZED_READ_ONLY_PREFLIGHT**, conditional on exact model-specific ordinary-UI path and a new authorization for that one session | May record model/year/head-unit software from owner documentation or the documented normal About/Version page. Do not include ADB, recovery, or display tests in the same authorization. |
| Recovery and historical diagnostic process | **NO_GO_UNRESOLVED_RECOVERY** | The old file was observed present in Phase R; current file and process state are unknown. Phase S's required boot/clock proof is not ready. No cleanup, process scan, retry, or reboot. |
| Honda ADB read-only diagnostics | **NO_GO_UNRESOLVED_RECOVERY** | Do not run Phase R refresh, Phase S, or P2-C5/V5 until exact prerequisites and a separate one-use authorization are reviewed. This packet specifies their possible scope for planning only. |
| Type111/session/security/rendering/installation | **NO_GO_UNRESOLVED_SECURITY** | No authentic source, production crypto, supported delegation seam, Display 1 admission, warning priority, or recovery path. No phone, rendering, app install, or candidate execution. |

## Evidence basis: what exists and what it does not prove

### Identity and software baseline

The exact vehicle/head-unit/cluster variant is not established by this checkout. The first useful observation is therefore limited to operator-held owner documentation or the normal user-facing About/Version page after the exact variant and documented menu path are known. Do not use dealer/service menus or infer the variant from an old screenshot or an unrelated Honda build. Record model year, trim/cluster and head-unit software identifiers; redact VIN, serial number, account data and other personal identifiers from the report.

### Historical executable and recovery state

The previous Test A transferred and invoked a diagnostic executable, but its evidence did not prove process absence or cleanup. A later, separately authorized Phase R inspection found the exact file at `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`, regular file, mode `0555`, `shell:shell`, 7,904 bytes, matching MD5 `6137a693a77646aaf9a4cf0f351731d4`. Remote SHA-256 was not measured. Those are historical observations, not current state. No old PID or boot ID is preserved; current file presence and current process/relaunch state are unknown. `rm` plus ENOENT would not prove that an open executable mapping ended.

The Phase S proposal lacks its required fresh, independently reviewed clock-bound attestation. Separately, preserved runtime research identifies Linux `3.1.10+`; period-correct upstream 3.1 lacks `/proc/sys/kernel/random/boot_id`, a vendor backport is unproven, and the exact hash-identified Honda kernel artifact/source/config is not available at the documented local path. Do not probe the live unit for `boot_id` to bypass this offline gate. Even a valid later-boot proof could establish termination only of the prior invocation; it cannot rule out a later relaunch or establish today's process state.

**Recovery decision:** `NO_GO_UNRESOLVED_RECOVERY` for Phase S, Phase C, Test A/B, process inspection, cleanup, reboot, and every ADB vehicle observation at present. Safely account for the uncertainty by leaving the file/process state unknown and not interacting with it. Do not infer absence.

### Display 1, ownership, geometry and warnings

Saved Honda evidence records an HDMI logical Display 1 at 800×480 and full-frame logical SurfaceFlinger bounds. The paired physical cluster photo also showed gauges/status absent from the logical frame, so downstream composition/cropping is only an inference. The physical transform and safe rectangle are unknown.

Static analysis of the preserved `ExternalDisplayOutService` shows Honda-owned bottom/main/interrupt full-frame roots using window type 2006. The service owns its roots and its `onBind()` returns null. `ExternalDisplayApService` exposes control/status/meter callbacks but no arbitrary `View`, `Surface`, bitmap, frame buffer, H.264 stream, or FD rendering method. No public arbitrary-content cross-process endpoint was found. No preserved Honda framework policy source establishes whether an ordinary app's `Presentation` can be admitted on Display 1 or the z-order of another window relative to those roots.

API17 AOSP documents `DisplayManager`, `createDisplayContext` and `Presentation`; this gives a generic app an API shape, not Honda admission. AOSP API17 display-category selection is based on display type. `SYSTEM_ALERT_WINDOW` is dangerous in generic AOSP for window type 2006, while privileged window types may require signature permissions. Honda grant/policy behavior is unknown. `VEHICLE_RW` and `ACCESS_MAP` protection levels/grants are not established for a candidate package.

Existing warning/interrupt evidence proves Honda has its own interrupt root, not that an ordinary app cannot cover it. Priority relative to another type-2006 window, downstream warning composition, interrupt timing and physical protected regions remain unknown. Do not trigger a warning, create an overlay, or infer safe coordinates from the 800×480 logical frame.

### HondaHack and stock CarPlay interface

HondaHack 7.7.7's traced screen-cast path captures Display 0 at 400×240, transports a 384,000-byte ARGB bitmap through `MemoryFile`/`ParcelFileDescriptor`, then injects a regular View into Honda's existing externaldisplay main/interrupt hierarchy via Xposed. Its 584×191 image bounds are HondaHack layout-local dimensions, not a physical cluster rectangle. This is an in-process host modification; it is not a supported ordinary-app API and does not establish warning priority or a safe area. No HondaHack modification is proposed.

Static firmware evidence places Type110 session setup, iAP2, accessory authentication, CarPlay receiver setup and response serialization inside `jmcs`. The existing Type111 Setup path is treated as unsupported/ignored in the analyzed build; it is not an accepted authenticated secondary stream. No transferable authenticated channel or stock-session handoff was found in `libcarplay_proxy` or the exported service APIs. Honda's exported UI/control services are not evidence of a session-bearing Type111 delegation seam. No phone interaction or credential operation is part of this plan.

The candidate APK's manifest requests zero permissions and disables its application, activity and compositor service; the service and activity are non-exported. This does not demonstrate that Honda would admit an ordinary app or that a future app would need no permissions. The inspected APK is not to be installed or run on the Honda.

## Exact staged proposal

Each vehicle session below is independent. Authorization for one stage does not authorize another. All displayed ADB commands are frozen research proposals, **not instructions to execute now**. Before any future use, re-hash the exact collector/manifest at the then-reviewed HEAD, inspect dry-run output, bind the exact target and operator conditions, and obtain a new one-use authorization naming only that stage.

### Stage 0 — offline identity and package review (no vehicle contact)

1. Identify the exact head-unit/cluster variant from owner/purchase documentation already held by the operator.
2. Review the exact ordinary UI path in the model-specific manual. If unavailable, do not guess a menu or enter a service menu.
3. Re-hash the diagnostic artifact/collector/manifest and review the Phase R/Phase S packets and prior private evidence through already available local records only. Do not access the vehicle to refresh them.
4. Seek exact matching public/OEM documentation or recover the exact kernel artifact offline with provenance. Do not fetch or query the Honda to fill this gap.

**Expected output:** model/build candidates, cited document/manual revision, and whether a normal About/Version route is documented. **Stop:** inconsistent model identifiers, missing/uncertain menu path, or a source that requires service credentials. This stage is the only work completed by this planning task; it did not access external personal documents or contact a vehicle.

### Stage 1 — one user-facing identity observation (eligible only for a new exact authorization)

**Purpose:** establish the actual target variant and ordinary UI-reported head-unit software baseline before considering diagnostics.

**Operator action:** with the vehicle safely stationary and parked, use only the model-specific manual's ordinary Settings/About or Version path identified in Stage 0. Read the model year/trim/cluster and head-unit software version. Do not open service/dealer menus, acknowledge a prompt that changes configuration, connect a device, or navigate into diagnostic functions. If the documented ordinary path requires a setting change, stop.

**Interface/privilege:** built-in user-facing display; ordinary vehicle operator access. No ADB, package, process, file, USB or network interface.

**Possible side effects:** menu navigation changes the transient on-screen view/focus, may wake the display or create normal UI/event logs, and may expose unrelated personal information. It is read-only with respect to configuration only if the manual-described path is informational and no write/confirmation action is taken; it is not literally side-effect-free. Do not photograph screens containing VIN, account, contacts, or other personal information. Prefer a sanitized handwritten record.

**Expected output:** exact model/year/cluster identifier and software version from the displayed/printed source, with source and uncertainty recorded. **Stop:** values conflict, page requires a service/dealer path, prompt offers update/reset/configuration, unexpected warning appears, or any step departs from the approved path. Return to the normal user screen only using the standard Back action if safe; do not change a setting to restore it. An unexpected result ends the session and triggers human review.

### Stage 2 — Phase R exact diagnostic-file metadata (ADB; not currently eligible)

**Purpose:** refresh knowledge of the exact historical diagnostic path only. The prior Phase R result found the file present. This stage does not inspect or prove process state and is not cleanup authorization.

**Proposed fixed sequence from the existing Phase R packet** (future collector must match its reviewed hash `de230c8a97aa06ea5134bc11a0902d59b86eee437bec913e273e5c2fb3edfc15`; manifest hash `9018f587f86dc45079e25bc81450de6381932991ae9b0bfdcc838c51b9f71278`):

```text
adb version
adb devices
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell ls -ld /data/local/tmp
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell ls -ld /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell /system/bin/md5 /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f
```

The last command is issued only if parent/path metadata matches the expected exact regular file. Do not invoke the diagnostic. Do not add a command or fallback.

**Interface/privilege:** host ADB client/server; target `adbd` and shell UID. The existing packet requires one confirmed intended target, stable already-connected ADB, and an exclusive operator ADB window with no other terminal/app issuing ADB.

**Possible side effects:** `adb devices` can start/use the host ADB server and enumerate/poll attached devices; ADB may update host logs/socket/process state and change transport state. Each target shell command starts short-lived processes and may add system/adbd logs or consume resources. `ls`/metadata is intended not to write the file but filesystem atime behavior is mount-dependent; `/system/bin/md5` reads the executable contents and may update atime. Therefore this is a read-only content/metadata operation by intent, not guaranteed side-effect-free. No content write, permission change, transfer, signal or deletion is in scope.

**Expected output:** one of the packet's exact classifications: expected file present, exact path absent, unexpected file state, or unknown/ambiguous. The expected-file result is not process safety. **Stop:** multiple/unknown ADB targets, wrong serial/version, unavailable/unstable transport, permissions error, symlink/directory, metadata/hash mismatch, malformed/noisy output, stderr, timeout, or any stock-state concern. Preserve evidence privately; no retry, cleanup, process query or further ADB command.

**Present disposition:** no Phase R authorization is requested in this report. The user must separately authorize any future Phase R execution after offline review of exact hashes and operator conditions.

### Stage 3 — Phase S boot-continuity observation (blocked; do not run)

The existing Phase S packet's candidate target commands are:

```text
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell /system/bin/cat /proc/sys/kernel/random/boot_id
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell /system/bin/cat /proc/uptime
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell /system/bin/cat /proc/sys/kernel/random/boot_id
```

They would read boot identity/uptime to compare a conservative bound against the prior host failure timestamp, not enumerate processes. Each target invocation creates shell/cat processes, can affect adbd/system logs and host transport state. Procfs reads ordinarily do not persist file contents; however Linux may lazily generate `boot_id` on first read, changing kernel-internal state. Thus the sequence is not strictly side-effect-free. Missing/malformed values, changed IDs, host clock step, expired/missing attestation, timeout or ambiguous result must stop immediately with no fallback/retry.

**NO-GO:** the exact kernel build/backport semantics are not established, the source artifact was unavailable at its recorded local path, the private fresh clock attestation does not exist, and the packet itself says no valid attestation is present. Do not run these commands to discover whether the interface exists. First resolve exact-build kernel support offline, obtain independent review of a genuinely evidenced fresh clock-bound attestation, and obtain a new single-use user authorization for Phase S alone. Even a successful result cannot authorize Phase C without independent current process/relaunch safety evidence.

### Stage 4 — P2-C5 logical display inventory (ADB; blocked behind recovery and separate review)

The existing collector/manifest hashes were verified locally: collector `39278b643a58b7f32bf624a6fa04ea90da26f7dedbb91518ed05c24a4576383b`; manifest `e136920f4eb61afbacebc998f2efce72c006fca1fd963ff349049d047daed8a4`. Its exact future command sequence is:

```text
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> get-state
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell id
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell getprop ro.build.version.sdk
adb -s <EXACT_OPERATOR_CONFIRMED_SERIAL> shell dumpsys display
```

**Purpose/interface/privilege:** record the target state, shell identity, reported API level and logical display service dump using target shell. The collector expects one exact serial, `uid=2000(shell)`, API 17 and nonempty display output. `dumpsys display` is a read-only service dump, not a request to create a display or launch an app.

**Possible side effects:** ADB may start/use a host server and poll/alter transport state; `get-state` can cause target transport interaction. Each shell/builtin command changes transient process state and may produce logs. `dumpsys display` makes Binder/service calls and can add CPU/memory/load or service/log activity while serializing a dump. It does not intend to write files, settings, windows or package state, but cannot be called side-effect-free. Preserve raw output only in the approved private evidence location, mode 0600; sanitize serials and personal/device identifiers in any report.

**Expected output:** logical display IDs/types/modes only, if supported by the exact target and permission. **Stop:** no exact target/ADB exclusivity, wrong shell UID/API, empty/unknown dump grammar, permission denial, timeout, unexpected stderr, transport anomaly, warning or abnormal stock state. No broad `dumpsys`, `dumpsys window`, SurfaceFlinger dump, screenshot, `service call`, `pm` query, setting, app, display or rendering action is included.

**Limit:** a successful dump establishes logical enumeration only. It does not prove a normal app can create a display context/window, obtain a token, show a `Presentation`, survive display removal, see physical pixels, or preserve warnings. The existing P2-C5 plan explicitly defers this query until shared-ADB and target-state risks are accepted. Current recommendation is **do not run** it while recovery is unresolved.

### Stage 5 — ownership, geometry, warning, CarPlay and permissions (offline first)

| Question | Proposed evidence action | Interface/side effects/privileges | Expected result and stop rule |
|---|---|---|---|
| Factory external-display ownership | Review preserved `ExternalDisplayOutService` manifests/decompiled source, HondaHack static trace, and saved captures; no vehicle query | Offline files only; no vehicle effects or target privilege | Confirms OEM full-frame roots and lack of arbitrary-content Binder endpoint. Stop if provenance/build identity does not match; do not call an exported service. |
| Physical geometry | Review matching OEM documents and existing calibrated/paired evidence only | Offline source review. No screenshot, camera observation, calibration pattern, or display write | Current evidence gives logical 800×480, not physical crop/transform. If authoritative physical transform/protected region is absent, keep geometry UNKNOWN. |
| Warning priority | Review OEM framework/policy source and static root ordering; do not provoke warnings | Offline files only. No `dumpsys window`, overlay, warning trigger or test pattern | Current warning precedence/z-order is UNKNOWN. If no authoritative proof, stop and retain NO-GO for any window/rendering test. |
| Stock CarPlay session interface | Review exact-build static ownership/call graph and exported Binder interfaces already preserved | Offline binary/source analysis only; no runtime access or credentials | `jmcs` owns iAP2/auth/Type110 SETUP; no transferable authenticated channel found; Type111 is unsupported in analyzed SETUP. If exact artifact identity is not verified, don't generalize. |
| Type111 delegation | Require documented, supported OEM/Apple interface and evidence of secondary-only handoff retaining Type110 | Offline documentation/contract review. No iPhone, USB, auth challenge, session request or stream | No supported interface is currently evidenced. Do not advertise Type111, synthesize an authority, or use HondaHack/Xposed as a substitute. |
| Candidate permissions | Inspect local candidate APK/manifest/signature with build tools already on host; no vehicle package manager | Host file read only; no target privilege | Existing candidate: zero declared permissions; app/activity/service disabled, service/activity non-exported. This does not prove Honda permission/signing grant. Stop before install or target `pm` query. |

These reviews do not need to be combined into a vehicle session. If future evidence requires a target-side query, define one narrow question, exact command, side-effect analysis and separate one-use authorization for that query alone.

## What must be resolved before a rendering or installation test

All of the following are required and conjunctive:

1. Exact vehicle/build identity and matching Honda framework/service/kernel evidence.
2. Close or safely account for historical executable/file/process uncertainty with independently reviewed evidence. Do not assume absent. The Phase S path also requires exact kernel support and fresh valid attestation; Phase C is a separate authorization and remains prohibited here.
3. Supported ordinary-app Display 1 discovery/admission and effective package signing/permission requirements. Enumeration alone is insufficient.
4. OEM-supported stock external-display owner/interface or an independently proven ordinary-app window contract. No host-process injection, HondaHack/Xposed, `jmcs`, framebuffer writes or undocumented privileged bridge.
5. Authoritative physical safe-area/transform and warning/interrupt z-order/priority, with a clear/stop path that cannot cover factory content.
6. A supported authenticated Type111 delegation source that leaves Type110/iAP2/auth/audio/Siri/call/touch/steering ownership intact, plus evidenced per-stream security/crypto semantics from an authorized source.
7. Display/app crash, disconnect, stale-frame, process death, memory pressure, warning, display removal, restart and recovery behavior on a representative supported target, followed by a separately designed installation/uninstall/restore procedure and owner.

Absent any item, stop at static review. A new installation/rendering experiment requires a separate proposal, independent ECC safety review and a new exact-scope user authorization; nothing in this document carries forward.

## Stop-condition checklist

Stop immediately and issue no further target command/action if any applies:

- The exact model/manual/software identity is missing, inconsistent, or requires service mode.
- ADB is not already stable, an exact target cannot be operator-confirmed, another device/client may be involved, or another terminal/app could issue ADB.
- The diagnostic file/path/metadata/hash differs from the reviewed identity, or current process/relaunch state remains unknown.
- The Phase S source/attestation is absent, expired, unsupported by exact kernel evidence, malformed, inconsistent, or clock bounds fail.
- Any timeout, nonzero result, unexpected stderr/output, empty or ambiguous parse, changed boot ID, transport event, permission denial, or collector/hash mismatch occurs.
- The normal display/cluster shows an unexpected warning or abnormal stock condition, or any UI step requests a setting change/update/reset.
- Any proposed step requires root, `su`, service menu, package install, launch, window creation, setting/file/process change, cleanup, reboot, USB/network capture, stock-process access, phone session or warning trigger.
- Evidence would contain VIN, serial, credentials, contacts, message data, auth material or unrestricted raw logs. Preserve only private minimum evidence; never commit raw vehicle evidence.

Unexpected output means stop, preserve the private result and return to offline review. No retry, fallback, alternate command, cleanup, or reboot is authorized by a failed step.

## Command authorization matrix

| Operation | Scope | Current decision | Required future authorization |
|---|---|---|---|
| Read owner documentation / exact model manual | Offline Stage 0 | Allowed as research; no vehicle contact | None for public/local documentation |
| Ordinary UI About/Version observation | One identity-only session | **GO only after separate exact authorization** | User authorizes one parked session, exact model/manual path, fields recorded, stop conditions and privacy handling; expires after session |
| Phase R diagnostic metadata refresh | Exact file/path metadata and conditional MD5 only | **No authorization issued here** | New single-use authorization naming current collector/manifest/artifact hashes, exact path/serial, ordered commands and operator-exclusive ADB conditions |
| Phase S boot/uptime observation | Three fixed procfs reads only | **NO-GO_UNRESOLVED_RECOVERY** | Exact kernel support review, fresh independent hash-bound clock attestation, re-reviewed package and separate single-use authorization |
| P2-C5/V5 logical display dump | Exact four commands above | **NO-GO_UNRESOLVED_RECOVERY pending review** | Recovery risk accepted, current packet hashes/dry-run reviewed, exact serial/operator conditions and separate single-use authorization |
| `dumpsys window`, SurfaceFlinger, screenshots or warning observation | Not part of current package | **NO-GO** | A new bounded evidence question, side-effect/privacy review and separate authorization; may still remain unsafe/uninformative |
| `Presentation`, overlay, APK install/launch, render, Type111/iPhone, cleanup or reboot | Vehicle modification/integration scope | **NO-GO_UNRESOLVED_SECURITY / NO-GO_UNRESOLVED_RECOVERY** | Not covered; requires separate architecture/safety design, recovery proof, ECC review and new exact authorization per session |

**No authorization can cover multiple later sessions.** A Phase R grant cannot carry into Phase S or display inventory; any display inventory grant cannot carry into window admission/rendering; recovery authorization cannot carry into cleanup or Test A. The user must issue a separate explicit authorization for each exact vehicle session after review.

## Independent ECC review

The independent ECC reviewer assessed the complete preflight proposal and exact four-file change set at HEAD `6cc9bc263e4e7f0974ababddc0466f5d3b0d77cd`; the reviewer executed no proposed vehicle commands. **Assessment: approved with the documentation correction recorded here.** The reviewer found the identity-only readiness code justified only for one ordinary, model/manual-confirmed user-facing identity observation after separate exact authorization. All ADB (Phase R, Phase S, and P2-C5/V5), recovery/process inspection or cleanup, Phase C, installation/rendering, and Type111 work remain blocked. The reviewer confirmed that the plan discloses incidental UI, host ADB, target shell, Binder/service, logging, transport, and possible filesystem/kernel effects; separates sessions and authorization; and does not treat HondaHack/Xposed, OEM window roots, or service exports as an ordinary-app rendering or authenticated Type111 API. The four-file inventory is exactly the two reviewed code/test files and these two reports. No code or test objection was raised. This review does not authorize vehicle contact. The correction supersedes the prior sentence that review was pending.

## Proposed commit and approval gate

Expected final change set:

1. `android/src/main/java/org/claritylink/android/DisplayPolicy.java` — fail-closed production warning admission.
2. `android/src/test/java/org/claritylink/android/OfflinePolicyTest.java` — assert caller-supplied approval cannot admit Honda rendering.
3. `research/implementation/claritylink-pre-vehicle-ecc-audit.md` — final audit, updated decision codes.
4. `research/implementation/claritylink-honda-preflight-readiness.md` — this exact-scope planning report.

Generated `build/` outputs and local signing keys are ignored and excluded. No other file should enter the commit. Proposed commit message: `fix(android): keep Honda display admission fail-closed`. The independent ECC reviewer approved the two code/test changes and the full four-file proposal, including the documentation correction recorded above. **No commit has been created. Human explicit approval is still required before committing this exact reviewed change set.** Any substantive file/diff change after review requires renewed approval.

## Formal recommendation

- **GO_FOR_PREFLIGHT_PLAN_REVIEW:** yes. The bounded proposal can be reviewed; nothing is executed.
- **GO_FOR_SEPARATELY_AUTHORIZED_READ_ONLY_PREFLIGHT:** limited yes for one ordinary user-facing identity observation after exact model/manual path is established and the user separately authorizes that one session. This is not ADB authority.
- **NO_GO_UNRESOLVED_RECOVERY:** yes for all ADB sessions, process-state claims, Phase C, Test A/B, cleanup and reboot until current recovery/boot/process questions are resolved under new, separately authorized scope.
- **NO_GO_UNRESOLVED_SECURITY:** yes for Type111 negotiation/delegation, authentication, CarPlay session access, display admission, rendering and installation until supported security/ownership/warning evidence exists.

The next user decision is review/approval of the proposed commit. Any future vehicle work requires its own separate, exact-scope authorization after the recovery gate; this report requests no ADB authorization and performs no vehicle action.
