# CL-INT-04: autonomous host-owned Display 1 withdrawal

Status: implemented and tested **offline, on synthetic content only**, with Python
process-boundary tests and Android API 17 (4.2.2) emulator instrumentation.
Tracked under issue #62. Builds on merged PR #92 (lease fence), #94 (Type111 ingest) and
#97 (ingest hardening). `safeForHonda()` stays `false`; `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`.

## Problem

CL-INT-03 expired a Display 1 lease only lazily, on the next read, and CL-T111-INGEST-01
adopted that expiry from `tick()` **in the producer's process**. A producer that died, hung
or went silent never read or ticked, so the lease only ended when someone else asked.
The host must withdraw by itself.

## Design (reuse, not a second lease system)

| Piece | Where | Role |
|---|---|---|
| `Display1LeaseHost` | `failsafe_coordinator.py` | The one lease/epoch/generation fence. Now locked, has `enforce_expiry()`, `next_deadline()`, `revoke_if_current()`, `generation_high_water`, and reports withdrawal failures. |
| `Display1HostService` | `display1_host_service.py` | Host-owned watchdog thread that calls `enforce_expiry()` on the host's clock. Never dies silently (errors counted, retried). Idempotent `stop()`; restart = new instance and new epoch. |
| `Display1HostServer` / `RemoteDisplay1Host` | `display1_host_ipc.py` | Unix-socket process boundary. A lease is bound to the connection that received it; the end of that connection (SIGKILL, crash, close) makes the host revoke **that** lease. `RemoteDisplay1Host` has the host surface used by `FailSafeCoordinator` and `Type111IngestPipeline` (injectable via `host=`), so there is no second code path. |
| `display1_host_process.py` | host process | Standalone synthetic host: `READY`/`STOPPED` lines, SIGTERM-clean. |
| `PaneLease` + `Display1HostLeaseGuard` | Android API 17 | `PaneLease` gains a host-looper expiry timer and `linkToDeath` revocation; the new same-package `Display1HostLeaseGuard` arms them for the backend's lease: `attach(gen)` arms a ttl, accepted frames renew it, `bindProducer(IBinder)` ties the lease to the producer process. Revocation reuses the existing `releaseView` path. `Display1OutputBackend` (a digest-pinned CL-R0 file) is unchanged. |

### Two independent withdrawal triggers

1. **Producer death:** connection end (Python) / `binderDied` (Android) revokes the bound lease immediately.
2. **Producer alive but silent or frozen:** the host timer revokes at `lease_seconds` / `no frame progress`.

Neither needs a producer `tick()`, heartbeat or cleanup callback.

### Invariants

* The fence closes before the cluster is touched: after `revoke()` no submit can be accepted, even if the cluster withdrawal then fails.
* A failed withdrawal is **reported** (`withdrawal_pending`, `withdrawal_failures`; `visible_content` stays truthful, grants are refused) and retried by the timer. `revoke()` still raises to a caller that owns cleanup reporting (the ingest pipeline).
* A stale owner's death or late frames cannot affect a newer lease: the death revoke is `revoke_if_current` (atomic), submits must come from the owning connection and match epoch + generation, and on Android the death link is removed when the lease ends.
* Reactivation: the host allocates every remote generation above its high-water mark under one lock (`grant_above`); a restarted producer's own counter restarts at 1 and is only a lower bound. Previous-boot leases fail on epoch, and a superseded or dead owner is fenced by connection ownership.
* Unknown is never "clean" or "withdrawn": `RemoteDisplay1Host.revoke` raises when the host did not confirm (cluster refused, or transport gone), and `status`/`residual_state`/`visible_content` raise when the host is unreachable. `FailSafeCoordinator._withdraw` still runs every independent closer before re-raising.
* Diagnostics are bounded (1024 in-process entries; the status reply carries the newest 32 plus exact counters), so a host that keeps failing cannot grow without limit or make its own status unreadable. Wire integers are exact ints below 2**53.
* Socket hardening: created under umask 0177; a stale path is removed only if it is a socket owned by this user that refuses connections.
* Type110 is not owned by this module: nothing here touches the primary display or decoder. Tests prove Type110 keeps decoding through withdrawal.
* Transport errors fail closed (reject; connection stays dead); bounded line, content, connection and error-log sizes.

## Evidence classification

| Category | Result |
|---|---|
| Synthetic lifecycle | **LAB**: Python process-boundary tests (`tests/integration/test_cl_int_04_host_withdrawal.py`) and API 17 emulator instrumentation (`Display1HostExpiryTest`, separate `:producer` process). |
| Type111 protocol handling | Unchanged; the real ingest pipeline is driven against the out-of-process host with locally generated lab bytes. |
| iPhone-origin video | **None.** No real iPhone bytes. |
| Honda receiver integration / Physical Display 1 | **None.** Nothing here touches a Honda, a vehicle, ADB or a connected phone. |

## Runtime evidence (synthetic lifecycle category only)

* Python: `tests/integration/test_cl_int_04_host_withdrawal.py`, 22 tests, stable over repeated runs. Real host and producer subprocesses cover: producer SIGKILL, orderly exit, silent-but-alive producer (host timer alone, `watchdog_enforcements >= 1`), restart after death, host-withdrawal failure and recovery, stale socket from a SIGKILLed host, Type110 operation through withdrawal with the real ingest pipeline.
* Android API 17 (Android 4.2.2 x86 emulator, private AVD): `Display1HostExpiryTest` 7/7 in each of 3 consecutive runs, plus the unchanged pre-existing PaneLease suite 7/7 against the modified `PaneLease`/`Display1OutputBackend`. ActivityManager logged the `:producer` process (separate pid) starting and dying for each death test, while the host instrumentation process kept running. The producer-kill test keeps renewing the ttl with frames, so only Binder death can end the lease there.
* Full offline gate `tools/run_tests.sh`, repository health, source discovery and whitespace checks pass on the final tree.

## Limits (honest)

* The backend's host-event listener is released at the next `attach`/`close`, not at expiry (it is inert once the lease is revoked).
* The Android host-side detach in `releaseView` still swallows a `detachContent` RuntimeException (pre-existing behaviour, unchanged here); a failed detach on the simulator is not retried or surfaced.
* Peers are trusted by filesystem permission only (same user, mode-0600 socket). A same-user process can supersede the lease; no peer-credential check is made.

* Epoch and lease remain staleness fences, not authenticators. The socket is mode 0600 in the caller's directory and assumes same-user peers.
* Lab controls (`--lab-controls`) and `--inject-withdraw-failures` exist only to exercise the synthetic host and are off by default.
* The Android binding is project-owned Binder code on a simulator; it is not the Honda process model, and no Honda Binder contract is claimed.
* The Android expiry timer depends on the host process's main looper being responsive; a wedged main thread is not covered.
* The Python `RemoteDisplay1Host` sends a compact text description of each frame, not pixels.

## Tests and how to run

* `python -m pytest tests/integration/test_cl_int_04_host_withdrawal.py`
* API 17: `tools/build_cl_int_04_host_test_apk.sh <fresh dir>`, install, then
  `adb shell am instrument -w org.claritylink.hostwithdrawal.test/android.test.InstrumentationTestRunner`.
  The PaneLease APK is intentionally unchanged (a contract test keeps it component-free).

## Next dependency

CL-INT-01 stays gated. This milestone removes the producer-liveness dependency from withdrawal;
it does not provide a Honda display contract or iPhone-origin Type111 input.
