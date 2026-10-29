# CL-FACTORY-02 — Codex integration handoff (synthetic navigation subsystem)

Status: public-safe. Scope: the offline, synthetic navigation-presentation
laboratory added by the CL-FACTORY-02 campaign. `safeForHonda() == false` /
`safe_for_honda() == False` remain non-negotiable and are preserved by every
component here. Nothing in this handoff authorizes vehicle, ADB, iPhone, or
factory-facing operations.

Branch: `claude/cl-factory-01-architecture` · PR: #76 (open, not merged).
Base: `origin/main`. This handoff describes code that is already pushed and
CI-checked on that branch.

## 1. Architecture overview

Three previously-independent primitives are now integrated behind one explicit
interface, plus a deterministic simulated host and an end-to-end demo:

| Component | File | Responsibility |
|---|---|---|
| Transport gate | `src/claritylink-transport/frame_gate.py` | per-generation freshness, bounded buffer, backpressure (pre-existing) |
| Nav state model | `src/claritylink-honda/cluster_navigation_model.py` | structured turn-by-turn state, visibility, warning withdrawal, recovery (pre-existing) |
| Fail-closed contract | `src/claritylink-honda/factory_integration_contract.py` | factory admission; always denies (pre-existing) |
| **Integrated pipeline** | `src/claritylink-honda/synthetic_navigation_pipeline.py` | **NEW** — coordinates the three above; four-way per-update outcome |
| **Simulated cluster host** | `src/claritylink-honda/simulated_cluster_host.py` | **NEW** — independent main + top-most interrupt layers, validity-gated rebuild |
| **End-to-end demo** | `src/claritylink-sim/cl_factory_02_demo.py` | **NEW** — reusable 16-step `run_demo()` returning a machine-checkable dict |

All are pure-Python, offline, synthetic. No Honda IPC, no Binder, no proprietary
identifiers, no real Display 1, no key material.

## 2. Public-safe interfaces (original, Codex-consumable)

### `synthetic_navigation_pipeline.SyntheticNavigationPipeline`
- `open_session(session_id:int, generation:int)` — generation is **lifetime-monotonic**
  (strictly greater than any generation ever opened, even across `restore_factory`);
  reuse raises `ValueError`.
- `set_host_available(bool)` — models synthetic display-host presence.
- `submit_update(*, generation, sequence, timestamp, maneuver, distance, unit, road_name="") -> UpdateOutcome`
- `on_warning()/clear_warning()`, `on_source_death()`, `on_host_lost()/begin_recovery()/restore_factory()`, `shutdown()`
- `presentation_eligibility() -> (bool, reason_code)` — **synthetic** host only.
- `safe_for_honda()` and `presentable_to_factory()` — both **always False**.
- `UpdateOutcome` fields: `admission` (`Admission`), `transport_status`
  (`FrameStatus|None`), `nav_status` (`UpdateStatus|None`), `presentation_eligible`
  (bool — per-update; a rejected update is never eligible), `presentation_reason`
  (str), `factory_decision` (`Decision`, always denied with
  `R_SAFE_FOR_HONDA_FALSE`).

### `simulated_cluster_host.SimulatedClusterHost`
- States: `NOT_INITIALIZED → DISPLAY_AVAILABLE → MAIN_CONTENT_ACTIVE / INTERRUPT_ACTIVE → DISPLAY_LOST → RESTORING → CLOSED`.
- `connect_display()`, `present_main(*, session_id, generation, content) -> PresentResult`,
  `withdraw_main()`, `clear_host()`, `activate_interrupt()/clear_interrupt()`,
  `lose_display()/begin_restore()/complete_restore(*, display_valid) -> bool`, `close()`.
- `main_presentable() -> bool` (fail-closed), `main_owner`, `interrupt_active`.

## 3. Data contracts — structured navigation vs Type111 video (DO NOT CONFLATE)

Two distinct representations, proven non-interchangeable by
`tests/honda/test_contract_type_separation.py`:

- **Contract A — structured navigation** (`cluster_navigation_model.NavigationUpdate`):
  semantic only — `generation, sequence, maneuver (ManeuverType), distance, unit
  (DistanceUnit), road_name`. No payload/pixels/codec fields. This is what the
  factory cluster consumes (CL-FACTORY-01 reports 04/06/08).
- **Contract B — Type111 video** (`frame_gate.Frame` carrying opaque bytes):
  `generation, sequence, timestamp, payload`. No semantic maneuver fields.

The nav model **rejects a `Frame` (or any raw payload) as `MALFORMED`** — there is
**no** video→TBT conversion anywhere, and there must not be. A legitimate
semantic-navigation producer is an **unresolved external dependency** (see §6).

## 4. Lifecycle & permission interaction

- **Ownership**: a presentation is owned by `(session_id, generation)`. Generations
  are lifetime-monotonic in both the pipeline and the host, so stale stream
  authority can never be resurrected after a warning, source/host death, or a
  display rebuild.
- **Presentation permission**: the pipeline distinguishes *synthetic* eligibility
  (our simulated host could draw) from *factory* permission (the contract, always
  denied). `submit_frame_to_factory` is denied by the `safe_for_honda()` guard
  even at the strongest hypothetical evidence tier.
- **Warning withdrawal**: a (synthetic) interrupt always wins, withdraws custom
  content immediately, and never depends on custom rendering completing. Clearing
  the interrupt does **not** auto-restore stale content.
- **Recovery**: host loss → withdraw + close transport; `begin_recovery` →
  `restore_factory` returns to stock; a **strictly greater** generation is required
  to present again.

## 5. Integration point for Codex's renderer

Codex owns the API17 renderer under `src/claritylink-renderer/android-api17/`
(package `org.claritylink.renderer`; e.g. `DecodedFrame`, `Display1OutputBackend`,
`FrameDispatchGate`, `SimulatedExternalDisplayCompositor`). The clean seam is:

> The Python `UpdateOutcome` (for accepted structured updates) is the **output
> contract** a renderer consumes. A Java mirror of `NavigationUpdate`
> (maneuver enum + distance + unit + road-name + generation/sequence) can feed the
> existing renderer's **main-content** path, while the renderer's interrupt/warning
> path stays owned by the factory-precedence model. Structured nav is **not** a
> `DecodedFrame` and must take a separate path from the video frame pipeline.

Do **not** route structured navigation through the decoded-video (`DecodedFrame`)
path, and do **not** enable any factory-facing output.

## 6. Concrete, limited Codex tasks

1. Add a Java data class `NavigationUpdate` (API17-safe, plain Java, no `android.*`)
   mirroring Contract A, with the same validation (non-negative gen/seq/distance;
   unknown maneuver → `UNKNOWN`; bounded road-name ≤ 256).
2. Add a renderer entry point that accepts that Java `NavigationUpdate` on the
   **main-content** path only, keeping the interrupt layer independent.
3. Keep the decoded-video (`DecodedFrame`) path and the structured-nav path as
   **separate** method signatures (no implicit conversion), mirroring §3.
4. Preserve fail-closed behavior: unknown/lost host state ⇒ do not present; a
   factory interrupt ⇒ withdraw main content.
5. Do not add any factory output enablement; `safeForHonda()` stays false.

## 7. Existing tests and commands

Run with the project's Python environment (pytest 9.1.1):

```
python -m pytest tests/honda/test_synthetic_navigation_pipeline.py -q      # 18
python -m pytest tests/honda/test_simulated_cluster_host.py -q             # 15
python -m pytest tests/honda/test_contract_type_separation.py -q           # 5
python -m pytest tests/integration/test_cl_factory_02_dual_stream_isolation.py -q   # 8 (scenarios A-H)
python -m pytest tests/integration/test_cl_factory_02_fault_matrix.py -q    # 24
python -m pytest tests/integration/test_cl_factory_02_end_to_end_demo.py -q # 4
python src/claritylink-sim/cl_factory_02_demo.py   # prints the machine-checkable demo result
```

## 8. Dependencies

- GitHub: `bmreyes25/ClarityLink`, branch `claude/cl-factory-01-architecture`, PR #76.
- Python only; standard library (dataclasses, enum, collections). No new deps.
- Does **not** touch Codex PR #74 or any runtime-performance files.

## 9. Android API17 readiness (honest status)

**BLOCKED this session — no API17 build evidence produced.** The compile path
(`tools/compile_android_api17_java.sh`) requires `ANDROID_HOME` with
`platforms/android-17/android.jar`, and no Java runtime was available in the
execution environment. The new logic is **platform-independent Python**; a passing
Python test is **not** API17 proof. The Java mirror in §6 is the next step and must
be compiled against API17 before any `API17_COMPILED` claim.

## 10. Safety requirements (unchanged)

- `safeForHonda()` / `safe_for_honda()` remain **false/False**.
- No factory-facing output is enabled; `submit_frame_to_factory` always denies.
- Synthetic warning priority here is **not** proof of real Honda safety behavior.
- No vehicle, ADB, iPhone, USB, Xposed, Frida, Binder, CAN, auth-bypass, or key
  extraction is used or implied.

## 11. Acceptance criteria for the Codex integration

- [ ] Java `NavigationUpdate` compiles under API17 with the §6 validation.
- [ ] Renderer presents structured main content and withdraws it on interrupt,
      with the interrupt layer independent and dominant.
- [ ] Structured-nav and decoded-video paths remain separate (no conversion).
- [ ] Fail-closed on unknown/lost host; no factory output enabled.
- [ ] `safeForHonda()` stays false; existing CI + CodeQL remain green.
