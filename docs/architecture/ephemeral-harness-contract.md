# CL-T111-EPHEMERAL-HARNESS-01: bounded offline integration contract

Task `CL-T111-EPHEMERAL-HARNESS-01`, spec revision
`001-genuine-type111-display1-ephemeral-harness-v1`.

Evidence label: **SYN** (offline synthetic/model only). `safeForHonda()` stays `false`;
status `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`. Nothing here is target evidence.

## What this is

A deterministic host-side cleanup/recovery state machine
(`src/claritylink-honda/ephemeral_harness.py`) and a machine-readable resource manifest
(`src/claritylink-honda/ephemeral_harness_manifest.json`). It runs on the development host only.

It reuses the CL-INT-04 stack unchanged (`Display1LeaseHost`, `Display1HostService`,
`Display1HostServer`/`RemoteDisplay1Host`, `FailSafeCoordinator`; see
`cl-int-04-host-owned-withdrawal.md`). There is **no second Display 1 lease system**: leases,
epochs, generations, connection-bound revocation and host-owned expiry are the CL-INT-04 ones.
The harness adds only an obligation ledger and the fault matrix around them.

## States

`IDLE -> ACTIVE -> FAULTED -> CLEANING -> CLEAN_MODEL | CLEANUP_INCOMPLETE`;
`CLEANUP_INCOMPLETE -> CLEANING` (resume); `CLEAN_MODEL -> ACTIVE`. Any other transition raises.
`CLEAN_MODEL` means clean **in the model**; the name is deliberately not "clean".

## Cleanup obligations (ordered, resumable, idempotent)

| Obligation | Storage class (model) | Cleared when |
|---|---|---|
| `producer_connection_closed` | n/a | the harness-owned producer connection is closed |
| `display1_lease_withdrawn` | n/a | the host's own status shows no lease, nothing visible, no residual, no pending withdrawal |
| `persistent_marker_removed` | PERSISTENT_DATA | the file existed and the harness removed it |
| `unknown_class_marker_removed` | UNKNOWN_PLATFORM | same; treated as persistent |
| `volatile_marker_removed` | RAM_BACKED_VOLATILE | the file existed and was removed, or the model wiped it in a simulated reboot |

Rules: a missing resource is `UNKNOWN`, never proof of a clean state (it cannot be told apart from
"never there"). An unreachable host or severed control connection is `UNKNOWN`, never "withdrawn".
`UNKNOWN` obligations are retried on `recover()` but do not self-heal.

## Fault matrix (all covered by `tests/honda/test_ephemeral_harness.py`)

| Fault | Expected model outcome |
|---|---|
| normal termination | producer ends via coordinator fault path; clean |
| process crash | host revokes on connection end ("producer connection lost"); clean |
| lost producer (silent) | host-owned timer on a manual clock withdraws; no producer action |
| lost control connection | `display1_lease_withdrawn` UNKNOWN, `CLEANUP_INCOMPLETE`, until re-observed |
| interrupted cleanup | stops after one step; resume completes; idempotent |
| host restart | new epoch; previous boot's lease fails with `REJECTED_EPOCH` |
| simulated reboot | host restart plus wipe of the one directory the model labels volatile |
| missing cleanup resource | `UNKNOWN`, `CLEANUP_INCOMPLETE` |

Epoch fencing note (reproduced defect, now covered): a freshly restarted host holding no lease
answers `REJECTED_NO_LEASE` before comparing epochs, so the epoch fence is only observable while the
new boot holds a lease. The harness grants a probe lease (`grant_above`), checks the previous lease
fails on epoch, then revokes the probe.

## Storage classes and what is NOT established

- **RAM_BACKED_VOLATILE**, **PERSISTENT_DATA**, **UNKNOWN_PLATFORM** are distinct in the manifest.
  Each is `target_established: false`, target status `UNKNOWN`.
- `/data/local/tmp` is **not established as reboot-volatile**. It is classed UNKNOWN_PLATFORM and
  treated as persistent until proven otherwise. No existing evidence shows what is mounted there.
- A **simulated reboot proves no Honda cleanup**. In the model it wipes one plain host directory.
  That is a model assumption. Persistent and unknown-class markers survive and remain obligations.
- Every outcome carries `NoTargetClaims`: `honda_cleanup_established`,
  `ram_backed_target_storage_established`, `restoration_established`,
  `reboot_recovery_established` and `safe_for_honda` are all `False`, in a frozen dataclass.

## Manifest rules

Sections: files, processes, sockets, services, mounts, display1_leases, cleanup_obligations, plus
`storage_classes` and `platform_unknowns`. Each entry has `scope` (`SYNTHETIC_HOST_MODEL` or
`HONDA_TARGET`) and `honda_dependent`. Every `HONDA_TARGET` entry is `UNKNOWN` with empty evidence.
`validate_manifest` rejects: a Honda-dependent property promoted without evidence, a synthetic
model labelled as establishing one, cited evidence files that do not exist, any true claim, any
target-established storage class, and `/data/local/tmp` as anything but UNKNOWN.

## Explicit unknowns before any target execution

Target process model; IPC endpoints; services and restart policy; mount table (tmpfs and `/data`);
whether `/data/local/tmp` survives reboot; Display 1 ownership/lease/withdrawal contract; target
cleanup, restoration and reboot recovery. All remain UNKNOWN and unestablished by this work.

## Out of scope (prohibited)

No Honda fields, authentication behavior, installable binaries, target patches, ADB, live-device or
connected-iPhone action, or compatibility claim. A passing host test is not target evidence, and
this contract does not authorize any vehicle-side step.
