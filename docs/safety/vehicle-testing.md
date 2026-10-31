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
setting change, installation, signal, or process attachment.

Stop the affected experiment immediately on identity mismatch, permission or
privilege surprise, unexpected persistence, command failure, timeout, engine
start/READY change, warning, connectivity/power anomaly, or abnormal factory
display/audio behavior. Do not retry, substitute, escalate, or proceed to
another phase. Preserve private evidence and use only the reviewed restoration
route. An abort permits host cleanup only; further vehicle commands require a
new reviewed decision. No tool powers off the vehicle or starts a second
session automatically.

## Access and evidence

For privileged reads, review the exact binary, policy/configuration, daemon,
prompt, logging and persistence behavior before execution. Read-only intent
does not make privilege acquisition read-only. If the access method is not
justified, leave that measurement unknown and continue work that does not
depend on it.

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
