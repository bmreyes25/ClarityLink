# CL-T111-LAB-02 — Negotiated Type111 media integration

## Scope and evidence

This offline integration composes the LAB-01 `LabDualDisplayModel` with the
existing `Type111IngestPipeline`. It uses generated `SYNTHETIC_LAB_CONTENT`
over a loopback socket, the existing host `Receiver`, its FFmpeg decoder, the
lease-gated simulated Display 1 host, and a separate Type110 output sink.
There is no Honda receiver, iPhone, Honda wire response, vehicle display, or
production hook in this path. `safeForHonda()` remains `false`.

The negotiation result remains `MODEL_ONLY`. The media test exercises real
host processes and OS sockets, including the existing FFmpeg binary. The
separate R7B C++ receiver test is reported as `HOST_NATIVE_TESTED`; it is
conformance evidence for that receiver, not proof that the LAB-01 Python
negotiation model runs inside the C++ receiver. The integrated Python pipeline
has not been executed on Android API17. This checkout has no API17 SDK, so no
API17 build or runtime result is claimed.

## Reused components

| Component | Existing responsibility | LAB-02 use |
|---|---|---|
| `LabDualDisplayModel` | Synthetic parent identity, `/info` policy, stock-first SETUP and Type111 child lifecycle | Owns the negotiated child and stock mock parent |
| `Type111SetupContract` | Prepared child, deterministic model listener reservation, serialization and rollback | Creates the model child before the integration serializer runs |
| `Type111IngestPipeline` | Receiver, actual loopback listener, clear-lab security, H.264 framing/decode, lease-gated output and cleanup | Owns the media listener, decoder, Type110 sink and Display 1 lease |
| `tests/integration/t111_synth.py` | Generated H.264 and lab framing | Supplies test-only VideoConfig and frame bytes |

The deterministic `ListenerReservation` has no socket. The receiver's
`HostListener` binds an OS loopback socket and owns the media connection. The
coordinator keeps their identities distinct; synthetic SETUP serialization
does not present either result as a Honda port or response.

## Ownership and sequence

The integration serializer runs after the model child reaches PREPARED. It
requires a Type110 receiver entry and prepares the existing Type110 receiver
first. The `SetupOrder` value preserves and exercises each synthetic SETUP
stream-list ordering; the shared media pipeline still establishes its stock
primary before a secondary can be committed. It then starts the existing
ingest pipeline's Type111 receiver path, verifies its
listener, security context, decoder and Display 1 lease, then attaches a
generation-bound cleanup handle to the prepared model child. Only after the
original synthetic serializer succeeds does the model child become ACTIVE.
Serializer failure stops that prepared child and closes only the Type111
ingest resources.

Malformed or oversized SETUP inputs are delegated through LAB-01's stock
fallback and do not allocate media resources. A Type111-only request without
an existing Type110 receiver receives the stock response and cannot commit a
child. If Type110 receiver preparation fails, the synthetic serializer is
never asked to serialize the Type111 candidate.

```text
synthetic parent open
  → model /info (Type111 opt-in required)
  → existing Type110 receiver ready
  → stock-first model SETUP
  → prepared model child
  → existing receiver listener + decoder + Display 1 lease
  → child owns generation-bound ingest cleanup handle
  → serialization succeeds; child becomes active
  → generated VideoConfig/H.264 → FFmpeg → lease-gated Display 1
  → child teardown clears Display 1 and closes only Type111 resources
  → Type110 listener, decoder, security and sink remain available
```

Parent teardown stops the model child first, then closes the full ingest
session. The cleanup handle captures the receiver session generation and does
nothing if delayed cleanup belongs to an older receiver generation.

## Identity map

`ComponentIdentity` keeps these values separate:

- opaque parent identity and model parent generation;
- model Type111 child generation;
- Type111 stream connection ID;
- receiver session generation and receiver stream generation;
- decoder identity, represented by `(receiver session generation, decoder
  restart ordinal)`;
- Display 1 lease epoch and lease generation.

No generation number is copied into another component's field. Receiver stream
and decoder identity are checked before media operations. Parent and stream
identity mismatches fail before the ingest pipeline is called. A closed B1
coordinator cannot send a late operation to a replacement B2 session.

## Verification matrix

The focused integration tests cover Type110-only startup, Type110-first and
Type111-first setup, generated frame dimensions/pixels and separate sinks,
mock stock response preservation, model-child ownership of the actual ingest
cleanup handle, listener and decoder setup failure, listener close after
SETUP, malformed VideoConfig and H.264, decoder failure, lease revocation,
wrong parent/generation/stream ID, duplicate SETUP, serializer failure after
receiver preparation, idempotent child teardown, host timeout, reconnect and
late B1 fencing, concurrent teardown, and full parent cleanup.

Type111-only failures are checked by sending a subsequent generated Type110
frame through the still-active primary listener and decoder. Parent cleanup is
checked against the receiver resource snapshot, ingest residual list, host
lease state, and visible content. This is host laboratory behavior only.

The R7B C++ receiver suite runs independently against its checked-in,
hash-verified synthetic media fixtures. It tests both stream setup orders,
separate output sinks, Type111 failure isolation, repeated cycles, malformed
media, production-security fail-closed behavior and zero final resources. It is
not wired to the LAB-01 negotiation model.

## Remaining boundary

No Android API17 build/runtime integration was available in this checkout.
The Android `Type111ControlPlane` remains a separate synthetic control/UI
model, not this media receiver. Honda session ownership, native `/info` caller
execution, receiver security, Honda display admission, iPhone acceptance,
physical Display 1 behavior and vehicle deployment remain unproven. Keep
`HONDA_TYPE111_NOT_PROVEN` and `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`.
