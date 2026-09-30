# ClarityLink digital twin role after Step 42B

## Purpose

The digital twin is the active, executable workstream while the target vehicle entry and display handoff remain unresolved. It supports deterministic development of protocol state, stream lifecycle, renderer behavior, failure recovery, and stock-primary invariants using synthetic inputs.

It is not a Honda runtime emulator and does not prove that a phone will negotiate Type 111 with Honda's receiver. It does not validate MFi/iAP2 authentication, Honda binary behavior, linker loading, Android Binder permissions, physical cluster geometry, or the availability of session keys in another process.

## Evidence profiles

Keep inputs labeled as one of:

- **Honda observed/static:** only behavior directly traced in preserved Honda sources, binaries, or approved captures. Type 110 Setup, the array-valued `/info` display field, and Honda's unsupported-Type111 skip behavior belong here.
- **Prior-art hypothesis:** MHI2 Type111 response and lifecycle concepts. These may inform candidate models but must never be presented as Honda wire requirements.
- **Synthetic:** generated sessions, stream IDs, descriptors, crypto placeholders, frames, and malformed input used to exercise code. Synthetic passing tests prove only the model's stated invariants.

## Current target architecture

The Step 42B target is jmcs integration for authenticated session/control ownership plus a renderer adapter in the ExternalDisplay host. The current implementation phase is **digital-twin only** until both process entry and frame handoff are proven. `LD_PRELOAD` is parked and does not define the model boundary.

```text
Honda-confirmed Type 110 model ──┐
                                 ├─ offline state/transport tests ─ renderer lifecycle model
MHI2 Type 111 hypothesis ────────┘                                  │
                                                                  synthetic Display 1 output
```

## Acceptance rules

1. Every Type111 response field carries an evidence label and an explicit unknown state until Honda evidence exists.
2. Type110 response semantics remain unchanged when a synthetic Type111 candidate is present.
3. Unknown display-to-stream identity does not silently default to a Honda UUID mapping.
4. Malformed, unsupported, or incomplete Type111 candidates fail closed and retain stock-only behavior.
5. Tests use generated fixtures; no proprietary capture, session key, or Honda binary is embedded.
6. A passing host test is never reported as vehicle or iPhone compatibility.

## What this work can establish

- Internal consistency of candidate control/transport state machines.
- Bounded parsing and cleanup behavior for synthetic ScreenStream and VideoConfig inputs.
- Renderer lifecycle behavior under synthetic frames, display loss, timeout, and teardown.
- Preservation of the modeled Type 110 response and stock center-render path.

## What remains outside the twin

- Whether Honda/iPhone negotiate a second descriptor and request Type111.
- The Honda-compatible response schema, correlation field, and key derivation for Type111.
- A legitimate path into jmcs and an authorized frame path into ExternalDisplay.
- Any live readiness or vehicle-safe rollback conclusion.
