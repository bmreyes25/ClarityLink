# CL-HONDA-111-01 → Codex: API17 pane-lease renderer task

Status: handoff only. Claude did not edit any Android file in this campaign. `safeForHonda() == false`; no Honda, Xposed, Binder, window-token or vehicle code is requested or permitted.

## Why this task exists

The merged API17 renderer already has the right seam (`Display1OutputBackend.Host`, `isNavigationPageActive`, `attachContent`, `FrameDispatchGate`). The synthetic Python contract in this campaign (reference implementation, below) adds three things the Java side lacks:

1. the host **reports** page and interrupt changes by callback instead of the renderer polling at call time;
2. withdrawal is a **lease revocation** that detaches the View and invalidates queued work, and recovery needs a **strictly newer pane generation**;
3. rejection is reported as **typed reasons**, not only exceptions.

None of this reaches the Honda cluster. It makes the renderer correct against a *simulated* host so that, if an authorized host contract ever exists, the renderer side is already proven.

## Reference contract (Python, tested)

- `src/claritylink-honda/navigation_pane_host.py` — `NavigationPaneHost`, `PaneLease`, `PaneOwner`, `DecodedFrame`, `Viewport`, `observe_contents`, `expire_observation`, `fit_rect`.
- `src/claritylink-honda/type111_pane_bridge.py` — `Type111PaneBridge`, `FactorySinkAdapter`.
- `src/claritylink-negotiation/type111_child_authority.py` — `ParentAuthority`, `Type111Child`.
- Tests: `tests/honda/test_cl_honda_111_01_navigation_pane_host.py`, `tests/integration/test_cl_honda_111_01_type111_pane_bridge.py`, `tests/negotiation/test_cl_honda_111_01_child_authority.py`.
- Documents: [display integration](cl-honda-111-01-type111-display-integration.md), [Navigation-pane contract](../../research/honda/cl-honda-111-01-navigation-pane-contract.md).

Dependency: Java base is PR #77, merged at `b9fa1a0b4aae11f71b257c3b7729470c5a8dc792`. The Python reference is on branch `claude/cl-honda-111-01-factory-receiver`; its exact head SHA is in the PR description. PR #79 (draft, `b4ebb94d…`), PR #75 and PR #74 are **not** dependencies.

## Files Codex may modify

Only these, none of which are in the file scope of PRs #74, #75 or #79:

- `src/claritylink-renderer/android-api17/Display1OutputBackend.java`
- `src/claritylink-renderer/android-api17/HondaStyleSimulatorRendererHost.java`
- new: `src/claritylink-renderer/android-api17/PaneLease.java`, `PaneEvent.java`
- tests under `android/src/test/java/org/claritylink/renderer/` (new files only)
- `src/claritylink-renderer/README.md` (one section)

Do **not** touch `android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java`, any workflow under `.github/workflows/`, `tools/run_cl_int_02_api17_ci.sh` or `tests/display/test_cl_int_02_*`/`test_cl_r12_*` (owned by open Codex PRs). If a change there looks necessary, stop and report.

## Required interface behaviour

| # | Requirement | Reference |
|---|---|---|
| 1 | `Host` gains a listener the simulated host calls with `PaneEvent` values: `PAGE_SELECTED`, `PAGE_DESELECTED`, `INTERRUPT_ON`, `INTERRUPT_OFF`, `HOST_LOST`, `HOST_RESTORED(valid)`. The backend subscribes in `attach()` and unsubscribes in `close()`. No event may be delivered to a closed backend. | `observe_contents`, `select_navigation_page`, `activate_interrupt`, `lose_display` |
| 2 | `PAGE_DESELECTED`, `INTERRUPT_ON`, `HOST_LOST` and a viewport change **revoke** the lease: the View is detached through `detachContent`, queued frames are discarded, and later `submit` calls fail with a typed reason. `INTERRUPT_OFF`, `PAGE_SELECTED` and `HOST_RESTORED` revoke nothing and **grant** nothing. | `_end_lease`, `clear_interrupt` |
| 3 | Recovery is an explicit `attach(newGeneration)` with `newGeneration` **strictly greater** than every generation previously used by this backend or host. A revoked `PaneLease` object is never valid again, whatever number it carries. | `acquire`, `next_generation` |
| 4 | `PaneLease.isValid()` is true only while the host's current lease is that object and none of the revocation causes has occurred. Callbacks run once, on the UI thread, with failures contained. | `PaneLease.add_revoke_callback`, `_run_contained` |
| 5 | Rejection reasons: `LEASE_INVALID`, `IDENTITY_MISMATCH`, `STALE_SEQUENCE`, `MALFORMED`, `UNSUPPORTED_STORAGE`, `GEOMETRY`. `submit` keeps throwing for programmer error and **returns** the reason for runtime rejection. | `PresentStatus` |
| 6 | `Viewport` provenance: only `SYNTHETIC_TEST_ONLY` is accepted, as today. A layout-local rectangle (for example a third-party app's own ImageView size) must be impossible to construct as a viewport. | `ViewportSource`, `LAYOUT_LOCAL_CANDIDATE` |
| 7 | `DecodedFrame.java` keeps its limits (3840×2160, 4 MiB, RGBA byte order, crop as left/top/right/bottom). Surface-backed frames stay rejected. No change to those limits without changing the Python mirror. | `MAX_WIDTH`, `MAX_HEIGHT`, `MAX_FRAME_BYTES` |
| 8 | Warning precedence: `FrameDispatchGate` already fences draws by warning epoch. Keep it; an `INTERRUPT_ON` event must also bump the epoch so a draw queued before the event is suppressed. | `FrameDispatchGate.setWarningVisible` |

## Generation mapping

The Python model has four generations; the Java backend has one. Use this mapping:

| Python | Java |
|---|---|
| parent generation | not represented; the host adapter owns it |
| stream generation | `FrameSource.nextFrame(generation)` argument (producer-owned) |
| config generation | `replaceGeneration(old, new)` on a changed `VideoConfig` (existing method) |
| **pane generation** | the backend's constructor/`attach` generation; must be strictly increasing for the life of the host |

If a single number is kept, it must be the **pane** generation, and `replaceGeneration` must remain restricted to config changes inside one lease.

## Tests required

New JUnit-style tests (same harness as `NavigationUpdateTest`) and, where already available, API17 emulator runtime through the existing `cl-factory-03` workflow without editing it. Minimum cases, each mapping to a Python test:

1. `PAGE_DESELECTED` revokes, detaches the View and rejects later `submit`; reselect grants nothing.
2. `INTERRUPT_ON` revokes; `INTERRUPT_OFF` does not revive; `attach(sameGeneration)` is refused; `attach(newer)` succeeds.
3. `HOST_LOST` revokes; `HOST_RESTORED(false)` keeps it down; `HOST_RESTORED(true)` still needs `attach(newer)`.
4. Viewport change revokes. A layout-local viewport cannot be constructed.
5. Malformed, wrong-identity, duplicate and out-of-order frames return the typed reason and leave the lease valid.
6. Surface-backed frame returns `UNSUPPORTED_STORAGE`.
7. Teardown order: `close()` then late event delivery is a no-op, and detach is called exactly once.
8. 100 attach/revoke cycles leave no retained View, frame or listener.

## Performance and resource acceptance

Do not add per-frame allocation to `submit`. Do not claim a performance result; run the existing CL-R12 gate (`tools/check_cl_r12_perf_gate.py`) unchanged and report its output. No new threads. Callback delivery must be on the UI thread, matching `requireUiThread()`.

## Explicit status

- Factory integration stays disabled. The only `Host` implementation used is the simulator host.
- No Xposed, no Honda Binder, no window token, no `TYPE_SYSTEM_OVERLAY`, no host interrupt or page-request notification, no CAN.
- The Python `FactorySinkAdapter` (always denies) has no Java counterpart and must not get one.
- `safeForHonda()` remains false.

## Report back with

Files changed, test results (host JUnit, API17 compile, API17 runtime if available), the CL-R12 gate output, the exact branch and SHA, confirmation that no file outside the list above changed, and any contract question this document did not answer.
