# R5X — Theoretical jmcs Type111 patch architecture

## Scope

**MODEL_ONLY · NOT_DEPLOYABLE · NOT_HONDA_BINARY · NOT_REAL_CARPLAY · NOT_MFI · NO_REAL_JMCS_PATCH.** This is a host-only theoretical model. It does not patch Honda jmcs. It does not prove Honda Type111. It does not implement real CarPlay authentication. It does not create a deployable receiver. It does not authorize a vehicle experiment.

The question is what state and ownership a hypothetical custom receiver would need if future governance and evidence allowed one. The [pure Python model](../../src/claritylink-sandbox/type111_patch_model.py) uses invented descriptors, port labels, security markers, frame strings, and an in-memory sink. It imports no Honda artifact, Apple private code, device API, network library, or media library.

## Non-goals

No binary or instruction patch, patch location, injection, callback replacement, loader/preload path, authentication, real socket, decoder, Display 1 window, APK, Honda runtime, or iPhone session. This design is not a recipe for target modification.

## Evidence basis

Rules v2 distinguishes `MODEL_ONLY` from `HONDA_STATIC` and observed evidence. [R3C](../../step-reports/43t1-r3c-static-entry-ownership-closure.md) found no additive same-session receiver entry; its NO-GO controls runtime work. [43P](../../step-reports/43p-current-ios-type111-oracle.md) observed simultaneous 110/111 on a separate Mac/iPhone lab receiver, with no Honda Type111 security conclusion. Existing [43R](../../step-reports/43r-type111-setup-listener-contract.md) and [43Q-B](../../step-reports/43q-b-type111-lifecycle-twin.md) are offline contracts. [R4C](../../step-reports/43t1-r4c-display1-access-static-review.md) leaves Honda Display 1 app admission and warning priority unproven. [Rules v2](../../docs/project/claritylink-rules-v2.md) bars evidence promotion and requires separate review and authorization for any future target step.

## Hypothetical receiver pipeline

```text
invented SetupRequest
  → preserve opaque Type110 model
  → explicit model-only Type111 decision
  → in-memory response tuple with optional 111 descriptor
  → mock listener label + mock security + mock decoder
  → mock Display 1 string sink
  → exact-generation teardown
```

These arrows are model state transitions, not recovered Honda interfaces. Type110 is treated as opaque data; the sandbox does not recreate its media/control/audio path.

## Setup interception model

The model starts *as though* a receiver had already supplied a parsed Setup request and Type110 response. It has no interception mechanism. R3C found no supported additive pre-serializer callback with session identity and cleanup. The `receive_setup` operation is a pure function over synthetic objects, not a Honda callback or serializer wrapper.

## Type110 preservation invariant

The first response descriptor is the same frozen Type110 object, and the opaque Type110 bytes are held by the same primary object through augmentation, Type111 failure, and teardown. This proves only an in-memory identity/equality property. It cannot prove Honda byte serialization, center display, audio, or runtime coexistence.

## Type111 Setup augmentation model

`request_type111` requires `enable_type111=True`. The child descriptor has type 111, invented `SYNTHETIC-` identity, and a deterministic integer port *label*. The response is a tuple containing the original primary descriptor followed by this child. Failure before commit restores the stock-only model response and clears prepared child state. No field is claimed as Honda schema.

## Type111 listener lifecycle model

The `Type111Listener` holds an integer label, a generation, `MOCK_ONLY` transport, and an open boolean. It neither binds nor accepts a socket. The label is derived from the synthetic generation for repeatable tests. A stale generation cannot tear down the current child. No target reachability or listener ABI is inferred.

## Mock security model

`MockSecurityContext` contains only `MOCK_SECURITY_NO_KEYS` and an active flag. It does not derive, hold, encrypt, decrypt, authenticate, or parse CarPlay material. Honda Type111 security remains unknown; 43P's modern parser branch is not transferred to Honda.

## Mock decoder/display model

`MockDecoder` accepts strings prefixed `MOCK_FRAME:` and returns `MOCK_DECODED:` strings. `MockDisplaySink` stores at most one string, and clears it on stale generation, lost source, failure, or teardown. It creates no pixel buffer, Surface, window, framebuffer write, or display connection. R4C's physical safe area and warning z-order unknowns remain.

## Teardown and cleanup ownership

The synthetic session owns its child listener, security, decoder, and sink. `TeardownManager` closes those by exact generation and is idempotent. Type110 is not owned or closed by child teardown. This models a desired contract; it does not show a Honda finalizer or callback that could enact it.

## Failure handling

In the model, absent opt-in leaves stock-only response; mock listener or augmentation failure drops only the child; stale frames clear the mock sink; lost source clears the sink; stale teardown leaves the current generation untouched; repeated teardown is a no-op. A failed mock frame validation raises `PatchError`. These tests do not cover real concurrency, serializer re-entry, network errors, process crash, warning occlusion, or target recovery.

## Why this is not deployable

The package has no target entry, protocol parser, socket, cryptography, decoder, Android/Honda display API, build output, or artifact writer. Names resembling patches or Honda paths are rejected. The sandbox cannot run as a receiver. Its integer port and frame strings have no wire meaning. The [invariants](r5x-type111-patch-invariants.md) and [failure matrix](../../docs/safety/runtime-failure-matrix.md) are evidence guards, not installation instructions.

## Evidence still missing for Honda

Honda Type111 response schema and acceptance; Honda Type111 security/framing; a same-session entry and lifetime owner; actual secondary listener behavior; stream-to-decoder handoff; Display 1 sink and physical protected area; warning/window priority; complete cleanup; stock Type110 center/audio coexistence. Any unknown stops a Honda compatibility or deployment claim. R3C's NO-GO and Rules v2 remain in force.
