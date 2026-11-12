# CL-T111-LAB-03 — API17 negotiated Type111 lifecycle integration

## Scope and evidence

This change brings the LAB-02 ownership and generation contract into the
existing Android 4.2.2/API17 laboratory receiver. It remains a synthetic lab
path: the API17 app uses generated H.264, project-owned Binder services, and a
simulated secondary display. It is not a Honda protocol endpoint and does not
establish iPhone-origin Type111. `safeForHonda() == false`,
`HONDA_TYPE111_NOT_PROVEN`, and `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` remain in
force.

`NegotiatedType111Lifecycle` is a narrow adapter attached to the existing
`Type111ControlPlane` and `CompositorService`. It does not create a second
compositor, network listener, decoder, renderer, or display lease. The current
`PaneLease` and `Display1OutputBackend` remain the presentation owners.

The adapter reports a delivered frame only after the existing compositor has
received a successful downstream Binder response from the existing View sink.
This is a receipt for the Android pipeline handoff. `PaneLease` remains the
authority for whether the synthetic Display 1 frame can be shown.

## Ownership mapping

| LAB-02 concept | API17 source of truth |
|---|---|
| Parent identity | The exact registered Type110 `FrameStreamIdentity` retained by the existing Type111 control plane. |
| Parent generation | An adapter-owned model generation. It is stored separately from the Type110 session and transport generations. |
| Candidate policy | Disabled when an adapter is created. The existing explicit lab capability registration opts in for that synthetic session. |
| Child generation | An adapter-owned generation assigned when the Type111 receiver sink binds, then advanced on transport replacement. |
| Stream identity | The exact Type111 `FrameStreamIdentity`, including connection and transport generation; stale identities are rejected. |
| Receiver readiness | The existing compositor accepts a live Type111 sink Binder and records its calling process. |
| Producer ownership | The existing compositor must authorize the optional isolated Type111 producer against the active parent and child before the adapter records its PID. A new producer Binder records a new producer epoch even when Android reuses the PID. |
| Decoder generation | Every accepted VideoConfig advances the adapter's decoder epoch. It is separate from the stream generation and is reset when transport identity changes. |
| Presentation generation | The adapter tracks selection changes independently. The API17 renderer's `PaneLease` keeps its own presentation lifetime and stale-frame gate. |
| Media delivery | A downstream-accepted RGBA frame advances the child receipt count. The H.264 fixture is generated lab content. |
| Child teardown | Existing child stream unregister closes the Type111 adapter state and records whether the Type110 stream remains registered. |
| Parent teardown | Existing parent-session teardown closes both streams and the adapter state; repeated close is inert. |

The generation fields are separate domains even if a particular run happens to
produce the same integer in two domains. No value is copied into another
component's identity field.

## Lifecycle and failure behavior

```text
Type110 parent authority active
  → explicit synthetic Type111 capability registration
  → validated Type111 SETUP pending
  → live Type111 receiver sink Binder accepted
  → optional isolated producer authorized for this parent and child
  → VideoConfig creates a new decoder epoch
  → existing navigation selection and PaneLease authorize presentation
  → downstream Binder frame accepted
  → Type111 child withdrawal, Type110 owner remains active
  → parent teardown revokes all session resources
```

The adapter rejects an unopted candidate, wrong parent session, Type111 using
the Type110 connection identity, duplicate setup, activation without a bound
receiver, stale transport or decoder generation, stale producer-death
notification, and frames after child withdrawal. A producer restart can bind
only after the existing compositor authorizes its new PID for the current
parent and stream. Child failure and withdrawal leave the Type110 owner state
available; parent teardown invalidates all child state.

The Type111 producer supplies its own private control Binder during compositor
authorization. The compositor validates its descriptor and process role, links
an identity-fenced death recipient, accepts the lifecycle producer bind, and
only then publishes the PID grant used by frame authorization. A repeated
authorization from the exact current Binder is idempotent; a different Binder
starts a new producer epoch, resets decoder and presentation state, and cannot
be revoked by a delayed death callback for the prior Binder. If a later stream
recheck prevents publication, the tentative lifecycle bind is rolled back.

When the current producer dies, the compositor revokes its exact PID, stream
identity, Binder, and death recipient, then fences the existing Type111 View
sink. The sink invalidates queued dispatch epochs, cancels pending UI work,
clears the last presented frame through the existing Activity target, and
rejects new frames until a replacement producer is authorized. This preserves
the Type110 parent and stream. When the sink accepts the fence, it rejects new
frames until the replacement Binder is authorized; if the clear callback fails,
the failure is reported and visual withdrawal remains unverified. Host tests
cover producer generation reset, stale death rejection, and dispatch epoch
invalidation; the Android Binder transaction path still requires runtime
execution.

These Android Binder death and rollback paths have not yet executed on the
guarded emulator. The runtime attempt stopped earlier, at renderer attachment,
before Type111 setup. The existing runner now requires a producer-death receipt
for LAB-03 once the presentation prerequisite is repaired.

## Verification

### Environment

The isolated `~/Android/r7c2-sdk` package inventory was verified before use:

- API17 platform revision 3 and `android.jar`.
- `system-images;android-17;default;x86` revision 7.
- Android build tools 35.0.0 and platform tools/ADB 37.0.1.
- Intel emulator 37.2.12 (build 16428233), executed under Rosetta.
- Temurin 17.0.20.1.

No SDK packages were installed or replaced. The first guarded AVD startup
failed before QEMU guest launch: the runner's default userdata allocation
required 12,288 MB while the host volume had 11,621 MB free. The follow-up
runner invocation requests a 4,096 MB data partition for its fresh, owned AVD;
the API17 system image and guest identity remain unchanged. A runtime result is
recorded only if the runner verifies the process, serial, API level, release,
ABI, and cleanup.

### Test inventory

`tools/test_cl_t111_lab_03_api17.sh` compiles and runs the adapter and control
plane contracts with Temurin 17. The existing `tools/test_r7c_java_api17.sh`
compiles the shared Android source against `android-17/android.jar` and runs
its Java contract tests. `tools/build_cl_imp_03_apks.sh` builds, DEX-converts,
signs, and checks the lab and disabled-candidate APKs, their permissions, and
their manifests. These builds establish API17 bytecode/build compatibility,
not Android runtime execution.

Runtime evidence is appended here only after the guarded scenario completes.
The guarded LAB-03 runtime attempt used the built APKs from this source
revision and reached the API17 x86 guest. The runner verified its owned AVD,
emulator process, serial, and API level; its existing Type110 owner-isolation
and owner-cap-recovery checks passed. The LAB-03 scenario did not reach Type111
setup. The app log recorded two displays and `WINDOW_ADMITTED_LAB`, then
`RENDERER_ATTACH_FAILED type=IllegalStateException`; the required borrowed
surface readiness marker and subsequent Type111 markers were absent. The
runner exited with failure at that first missing marker and cleaned up its
owned emulator resources. No Type111 runtime acceptance result is claimed.

This failure is in the existing presentation Activity path, outside this
task's file reservation. The host lifecycle contract tests and API17 bytecode
build remain useful bounded evidence, but they do not substitute for Android
runtime execution. A follow-up must diagnose the Activity renderer attachment
failure under its owning task before rerunning the Type111 scenario.

The runtime acceptance scenario, when unblocked, requires an actual producer
authorization, downstream frame receipt, Type110 progress after Type111 child
failure, and child/parent cleanup markers from the running Android services.

## Boundaries

- The emulator guest is x86, not Honda ARMv7/Tegra 3.
- The generated H.264 fixtures are not iPhone captures.
- The Type111 advertisement and SETUP behavior remain synthetic laboratory
  behavior.
- No live Honda session, Honda receiver hook, factory binary, vehicle, or
  connected iPhone was used.

## Producer-death review follow-up

Source revision `ee09e69e2d81b0dba7604f40b4830f39023a1940` received two
independent review findings: producer death did not itself fence the visible
Type111 frame, and a same-PID replacement Binder could inherit stale decoder
and presentation state. The follow-up implementation adds a private
same-UID-only sink fence transaction and makes Binder replacement advance its
own lifecycle epoch. Exact Binder matching protects against a delayed death
callback revoking its successor. API17 host contracts and the APK build pass
for the follow-up source, but the Binder/view interaction has not been
exercised on the emulator because the existing Activity attachment failure
occurs before Type111 setup.
