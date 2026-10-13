# ClarityLink vehicle evidence roadmap — R7E7I-VP

## Scope and current state

Planning only. No Honda ADB, vehicle commands, writes, execution, process enumeration, cleanup, APK installation, window creation, rendering, CarPlay changes, iPhone session, or new device contact occurred. Existing authorizations are not reused.

This plan spans recovery, display, and receiver ingress, so it is organized under a new `research/vehicle/` directory rather than nested under the narrower `research/runtime/`; existing architecture/runtime reports remain the evidence sources and are hash-referenced in the matrix.

Verified checkout: `bmreyes25/ClarityLink`, branch `architecture/r7e-parked-car-compatibility-preparation`, PR #19 open, starting HEAD `a973cd8883624e4f064f30e478de5cec2d54bbe7`, worktree clean. The immediately prior R7E7I remediation is complete and reports **PHASE_S_BLOCKED**, **CURRENT_PROCESS_SAFETY_UNKNOWN**, **PHASE_C_NO_GO**, exact old-path absence unproven, historical API17 timeout cause undetermined, and **TEST_A_BLOCKED_WITH_EXACT_REASON**. The private Phase R record is historical and says the file was present with expected mode/owner/size/MD5; no fresh target observation exists.

The P1 ingress conclusion remains `P1_C5_NO_GO_PENDING_NEW_INTERFACE_EVIDENCE`: stock `jmcs` owns authentication, USB/iAP2, Type110, and control; no authenticated external Type111 or route-guidance ingress was proven. PlayPort 43P is a lab result only. The desired active iPhone source cannot be inferred from Honda-native guidance or stock CarPlay operation.

P2 established that the logical Display 1 frame is 800×480 and the saved SurfaceFlinger rectangles cover that frame. It did **not** establish physical panel mapping, navigation-safe area, warning z-order, normal-app window admission, or visible rendering. P2-C5's frozen `dumpsys display` collector is reviewable for logical display inventory only; because current recovery/ADB process state is unresolved, defer its vehicle use until an explicit shared-ADB risk review.

P3 has host-side API17/ARMv7 and collector evidence only. The production ARMv7 diagnostic hash was previously verified. Emulator rehearsals cannot resolve Honda vendor permissions, process state, or display admission. The latest R7E7I assessment supersedes older conditional Phase S examples: illustrative clock error numbers in old packets are not evidence or authorization.

## Prioritized candidates

See the complete machine-readable matrix in [vehicle-test-matrix.json](vehicle-test-matrix.json). The ranking values information gain against risk and whether results change a decision:

1. **V0 — passive parked baseline.** Best next physical observation after separate review: document normal center/cluster state, navigation availability, and visible layout before any future experiment. A photo is a record of appearance, not a measurement of physical transform, layer order, safe area, or warning precedence. It cannot clear recovery gates.
2. **V1 — historical termination.** Potentially decisive only if authentic, independently reviewed historical and current clock bounds become available. They do not exist; keep Phase S blocked. Do not run the legacy packet from its illustrative bound.
3. **V2 — current process/relaunch safety.** Necessary after V1 but no proven unprivileged complete process visibility or no-relaunch basis exists. Do not prepare a broad `/proc` sweep or infer absence from `ps`.
4. **V3 — exact-path cleanup.** Existing Phase C proposal is conditional and blocked by V2, fresh identity, and separate single-use authorization. Do not clean up.
5. **V4 — ARMv7 Test A.** Blocked by V1–V3 plus unresolved historical timeout. Do not run automatically after cleanup.
6. **V5 — logical Display 1 inventory.** Existing four-command package can enumerate the service's logical view, but is deferred until the shared-ADB/process-state concern is reviewed and a new authorization is issued.
7. **V6 — stock composition/layers.** No justified narrow, build-verified command is frozen. Do not substitute broad `dumpsys`/SurfaceFlinger output or perturb warning/window layers.
8. **V7 — window admission.** Not ready. Public API17 `Presentation` semantics on AOSP do not establish Honda caller permission, token, coexistence, or safe geometry. APK installation would be a project-constraint change requiring explicit approval before any test package.
9. **V8 — passive stock CarPlay behavior.** A narrowly observed, already-existing normal session may tell us visible source/page behavior and lifecycle; it cannot establish Type111 or custom receiver support. Do not initiate or alter a session, intercept traffic, or read authentication material.

Only V0 has a scoped review-ready observation package; it is not an authorization. There are zero runnable Honda diagnostic, cleanup, Test A, window, rendering, or protocol packages ready for execution.

## Proposed session order

Session A: V0 passive baseline only. Stop and review before any further activity.

Session B: V1 only if clock evidence is independently accepted and a new one-time authorization is issued. Current state: blocked.

Session C: V2 only after offline review finds a narrow, permission-complete method and a separate authorization. Never launch it automatically after V1.

Session D: V3 cleanup only after V2 produces sufficient exact-file reference evidence, no-relaunch review, and a separate cleanup authorization. It cannot be combined with Test A or CarPlay work.

Session E: V4 Test A only after successful separately authorized cleanup, exact path absence, reviewed artifact/package hashes, acceptable timeout disposition, and a new Test A authorization.

Session F: V5 only after its shared-ADB risk is reviewed and a new one-time read-only authorization is issued.

Session G: V6/V7 and any active CarPlay/integration research require new evidence, independent safety review, and separate approvals. Window creation/rendering and a new CarPlay receiver are not prepared here.

## Rejected approaches

- Empty `ps` output or a broad process-name sweep as proof of executable absence: neither establishes complete procfs visibility, exact inode identity, nor future-launch exclusion.
- Root, `su`, ptrace, process kills, reboot/power-cycle, or battery disconnection to manufacture termination evidence: these are outside the allowed scope and change system/process state.
- Broad `dumpsys`, generic WindowManager/SurfaceFlinger dumps, screenshots, warning induction, or overlays as a shortcut to physical safe geometry or warning priority: output is unbounded/undemonstrated and the physical transform remains unsupported.
- USB/network interception, private auth-material access, `jmcs` hooks/replacement, or a competing CarPlay receiver: no lawful interface/authorization or stock coexistence proof is established.
- An exploratory APK/window/test pattern: violates the current no-APK constraint and would render over a region whose safe area and warning precedence are unknown.
- Automatic V1→V2→V3→V4 chaining or combining cleanup with Test A/CarPlay: each has a separate evidence gate, stop, review, and authorization boundary.

## Goal boundary

The architecture goal remains stock Honda CarPlay on Display 0, authentic iPhone navigation on Display 1, and normal audio, Siri, calls, controls, and vehicle-critical instrumentation. Existing evidence does not prove an authentic secondary source or a safe Display 1 surface. The plan explicitly avoids claiming support where the Honda's interface, authentication, permission, transform, or warning policy is unknown.

**Decision: `VEHICLE_READ_ONLY_PLAN_READY_FOR_REVIEW`.** This means V0's passive checklist/template and the evidence roadmap may be reviewed. It does not mean any vehicle operation is authorized or that blocked candidates are ready.
