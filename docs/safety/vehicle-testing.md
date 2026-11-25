# Vehicle testing and diagnostic sessions

ClarityLink's engineering goal is genuine iPhone-origin Type111 navigation on
factory Display 1 while preserving stock Type110 behavior and factory safety.
Testing evidence must show what was actually observed. A completed command or
green run status is not evidence that Type111 was negotiated or displayed.

Use the [three-level experiment workflow](experiment-risk-levels.md) for
ordinary preparation, one session-level owner approval, and proportionate
review. This page records the vehicle-specific operating limits.

## Current scope

Offline analysis, host tools, synthetic tests, and emulator experiments may
proceed without additional vehicle permission. A live vehicle or iPhone action
requires an explicitly selected experiment and one current owner-approved
scope. The October 31 controller now has a fixed live backend, but it accepts
only an exact private one-use session record with current pins, required review
artifacts, and interactive readiness confirmation. No current session has
passed those gates; dry-run or simulation grants no live permission. Historical
C-P approval and ledger records remain untouched and cannot authorize a new run.

`safeForHonda() == false` and `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` remain in
force. This deployment gate does not prevent offline engineering or a
properly scoped diagnostic session.

## Session checks

Before a live experiment, identify its unanswered question and expected
evidence. Present the exact action list, target/endpoint, likely side effects,
stop conditions, evidence destination, and restoration route. Obtain one fresh
owner decision for the session. Keep any action beyond that scope out of the
run until separately reviewed and authorized.

The owner must be physically present; the vehicle must be stationary in Park,
parking brake set, in the reviewed power state, and factory displays, cluster,
Navigation and audio normal with no abnormal warning. Do not test while
driving. The owner performs ordinary phone and UI transitions. Use only an
already authorized ADB endpoint and exact target identity. No scanning,
fallback endpoint, retry, `adb root`, arbitrary shell, unapproved `su`, target
setting change, installation, signal, or process attachment. The separate
CL-HONDA-ROOT-ACCESS-V2 fixed profile is the only proposed `su` exception: it
requires the exact archived digest and path, owner/mode metadata, a read-only
covering mount, a non-symlink path chain, non-writable parent directories,
fresh source pins, one session authorization with explicit SuperSU side-effect
acceptance, and a final one-use readiness confirmation. It stops rather than
repairs permissions, changes mounts, or falls back if any check differs.

For the comprehensive Honda campaign, stop immediately on identity mismatch,
permission or privilege surprise, unexpected persistence, command failure,
timeout, loss of the approved READY-active state, loss of Park or parking
brake, abnormal warning, unexpected engine/exhaust behavior, connectivity/power
anomaly, or abnormal factory display/audio behavior. READY active is expected;
loss of READY is the stop condition. Do not retry, substitute, escalate, or proceed to
another phase. Preserve private evidence and use only the reviewed restoration
route. An abort permits host cleanup only; further vehicle commands require a
new reviewed decision. No tool powers off the vehicle or starts a second
session automatically.

## Access and evidence

For privileged reads, review the exact binary, policy/configuration, daemon,
prompt, logging and persistence behavior before execution. Read-only intent
does not make privilege acquisition read-only. V2 classifies the archived
06777 mode as a high permission risk even when a current read-only mount
prevents unprivileged replacement. The exact V2 authorization accepts possible
SuperSU prompts, daemon activity, policy/request/log state and persistent
target writes. A hash check reduces substitution risk but does not prove
race-free immutable execution or zero-write behavior. Leave the measurement
unknown if any V2 gate fails.

## Focused root observation: CL-HONDA-ROOT-ACCESS-V2

This is a Level 2 controlled diagnostic, not deployment authorization. It
answers which process-owned sockets, receiver mappings, and Android display
resources correlate with a normal stock iPhone CarPlay session. It performs
three snapshots: disconnected baseline, normal wired CarPlay connected, and
normal disconnect. It reads bounded `jmcs` identity/maps/fd links, `/proc/net`
socket tables, and `dumpsys display`, `window`, and `SurfaceFlinger`. It does
not read memory or credentials, attach to a process, change settings, capture
packets, or modify the receiver. Exact fd-inode matches to network-table rows
are evidence of process ownership; the transport role must still be established
from phase behavior, not guessed from ports.

Before an owner session:

1. Review revision 2.2 of `tools/honda-readonly-preflight/root_access_v2_profile.json`.
   Make a private, non-expiring draft with
   `python3 tools/honda-readonly-preflight/root_access_v2.py --authorization <private-draft-json> --make-authorization-draft`.
   This contacts no device and leaves endpoint, expiry, risk acceptance,
   power-state and all owner/readiness fields blank or false. Run
   `python3 tools/honda-readonly-preflight/root_access_v2.py --serial <exact-private-endpoint> --authorization <private-draft-json> --dry-run`
   once the owner supplies the exact already-authorized endpoint. At the car,
   after physical readiness confirmation, create a fresh run ID and expiry
   within 15 minutes, enter the exact endpoint, acknowledge the named risk,
   and set the approval/readiness fields. Bind the authorization to the current
   profile/source-lock hashes and target properties. Keep it mode 0600 in an
   owner-only directory. A draft is not authorization.
2. Prepare an existing owner-only evidence parent directory (mode 0700), a new
   output path beneath it, and the local consumed-run ledger. Use the exact
   already-authorized endpoint; do not run `adb devices` or switch transports.
3. Outdoors, park, set the parking brake, keep the brake pedal released and the
   power system ON with READY absent. The owner remains present. If ADB or the
   approved root path is unavailable in this state, stop without enabling
   READY, changing settings, or trying another endpoint. Confirm center display,
   cluster, Navigation and audio are normal with no warning.
4. Start the runner once with the exact endpoint, private authorization and
   new output directory. Type `YES` to durably consume the session ID, then
   follow its three prompts. Use normal wired CarPlay connect/disconnect only.
   The reviewed live invocation is
   `python3 tools/honda-readonly-preflight/root_access_v2.py --serial <exact-private-endpoint> --authorization <private-0600-json> --output <new-directory-under-private-evidence-parent>`.
   Collect after each transition has settled; do not type `READY` during a
   transition. Stop on any unexpected warning, process/target identity change,
   privilege prompt/denial, command error, timeout, output limit or abnormal
   display/audio behavior. There is no retry or automatic cleanup command.
5. The runner preserves bounded raw output privately, with 0700 directories,
   0600 files and SHA-256 inventory. SuperSU daemon, policy, request or log
   effects may persist; the runner does not delete or reverse them. Restore
   stock CarPlay and the factory UI with ordinary controls, then follow normal
   owner power-off guidance. Analyze raw endpoint/socket details locally; only
   sanitized counts and conclusions may enter public Git.

The local checks establish command bounds and fail-closed behavior only. They
do not authorize a live run or prove Honda behavior. A fresh owner-approved
session is still required.

Revision 2.2 budgets exactly 141 ADB commands: 24 target-identity reads, 16
mount/path/mode/hash assessment reads, 86 `su` invocation plus immediately
preceding digest reads, and 15 display/network reads. The runner and profile
both enforce that reviewed limit; there is no silent allowance change. The
API-17 Toolbox parser follows the Android 4.2.2 source format: numeric long
regular-file output has mode, UID, GID, size, ISO timestamp and basename,
without a link count; the root directory basename is empty. The host parser
also accepts the fixed directory-row form with numeric UID/GID and timestamp
but no size, while the `su` regular-file size remains mandatory. Unknown or
ambiguous layouts stop preflight. See the upstream
[Android 4.2.2 Toolbox `ls.c`](https://android.googlesource.com/platform/system/core/%2B/android-4.2.2_r1.2/toolbox/ls.c).
The fixed `su` digest operation is `/system/xbin/busybox sha256sum
/system/xbin/su`; it has no utility-path fallback. Missing BusyBox or its
`sha256sum` applet fails the preflight before any SuperSU invocation.

## Separate HondaHack UI observation

This is a distinct Level 2 UI-only experiment and does not require root or ADB.
It uses the already-installed HondaHack only through its ordinary Start/Stop
Casting controls and the factory Navigation control. No settings, services,
packages, Xposed configuration, warning behavior, or display geometry are
changed. The existing workflow requires qualified technical/safety review for
this Display 1 observation and one separate owner session approval.

Record a private visual baseline with normal factory Navigation, cluster,
center display and audio. In order: enter factory Navigation; start casting
once through HondaHack's normal UI; observe the current display hierarchy;
exit Navigation using its ordinary control; re-enter Navigation; stop casting
once through HondaHack UI; and verify normal factory restoration. The owner
performs each action and collection occurs only after the screen settles. Stop
on any warning, flicker, lost controls, abnormal audio, unexpected service
behavior, or failure to restore. Do not trigger a warning, restart the display
service, use ADB/root, reinstall HondaHack, or change Xposed. This measures the
existing attachment's visible ownership/withdrawal behavior; it does not feed
Type111 video or establish permission to install ClarityLink.

Keep raw and derived vehicle output outside Git in a private directory. Limit
collection to data that answers the question; bound time and output; inventory
and hash retained evidence. Public summaries must omit serials, identifiers,
endpoints, raw procfs/log output, images, credentials, keys, and private Honda
details. Never publish data just because it is ignored by Git.

## High-risk changes

Receiver or runtime modification, process injection, display ownership
changes, firmware/persistent changes, warning behavior, or vehicle-control
effects require Level 3 review, explicit owner approval, and independent
recovery evidence before any vehicle use. No diagnostic session authorizes
deployment. CAN transmission, deliberate warning interference, and driving
tests remain prohibited.

## Historical campaigns

The C-P campaign, its 135-command manifest, approval, ledger and evidence are
historical records. Do not alter or reuse them. The distinct comprehensive
campaign retains all eight research phases; its fixed live backend is
authorization-gated and no current session is approved. Read [its current
experiment status](../diagnostics/comprehensive-runtime-campaign.md).
