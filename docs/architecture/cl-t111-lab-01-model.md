# CL-T111-LAB-01 — offline negotiation and lifecycle model

## Scope and evidence class

This unit composes ClarityLink's existing stock-first mock SETUP delegator,
generation-owned Type111 child lifecycle, deterministic listener allocator,
and Type110 stock fixture. The model returns Python mappings only. It does not
serialize an Apple/Honda `/info` response, open a network listener, create a
Honda session or Screen, derive security, run an iPhone, or enable production
hooks. Every result is `MODEL_ONLY`; `safeForHonda() == false` remains in force.

The primary is a fixture-owned Type110 mock. Type111 is a separate project child
keyed by its lifecycle generation and listener reservation. The model's
readiness booleans represent synthetic test prerequisites; they are not
cryptographic, Honda receiver, display ownership, or vehicle readiness proofs.
The existing API17/host synthetic receiver and decoder remain separate accepted
components and are exercised as regressions; they are not silently attached to
the mock parent by this model.

## Contract

| Boundary | Contract |
|---|---|
| Parent | `open(identity, generation)` binds one opaque parent token to one positive generation. Calls using another token or generation fail before stock SETUP. Each reconnect uses a fresh model instance. |
| `/info` candidate | Default policy is `DISABLED`. `MODEL_ONLY` adds the synthetic Type111 descriptor only when the parent is active, the capability explicitly uses `SYNTHETIC_LAB`, and listener allocator, independent child-security owner slot, and secondary display adapter readiness are all present. The stock mapping and Type110 descriptor are copied unchanged. |
| SETUP | Stock-first behavior is delegated to `StockFirstType111Delegator`. Type111 is considered only if the same generation previously received a candidate and readiness still holds. The existing setup contract must reserve a `LISTENING` model listener and prepare a generation-owned child before invoking the serializer. |
| Failure | Invalid, oversized, duplicate, stale, unready, listener-failed, and serializer-failed child attempts return the exact stock Type110 fixture response when the mock stock owner is still live. No second stock call is made after a delegation exception. A committed child is not replaced by duplicate SETUP. |
| Teardown | Type111 teardown closes only its child listener/screen lifecycle. Parent teardown revokes the stock mock and all child-owned resources. Reconnect is a new model/generation; old model tokens cannot act on it. |
| Native adapter | `HondaNativeReceiverAdapter` is a protocol declaration only. It requires proof of genuine parent identity, stock-result ownership, explicit readiness, per-call policy, child lease creation/withdrawal, and generation invalidation. No implementation currently binds it to Honda. |

The model's listener allocator assigns deterministic fixture ports; it does not
bind sockets. A candidate descriptor is not a live child. SETUP output is
withheld unless the child listener reservation has reached the contract's
`LISTENING` state. A separate synthetic security-owner availability flag does
not supply key material or establish any CarPlay cipher, nonce, or wire
security profile.

## State flow

```text
NEW
  └─ open(parent token, generation) → PARENT_ACTIVE
       ├─ /info disabled or readiness incomplete → STOCK_INFO_ONLY
       └─ explicit MODEL_ONLY + all prerequisites → CANDIDATE_AVAILABLE
            ├─ Type110 SETUP → STOCK_RESPONSE; Type110 owner unchanged
            └─ Type111 SETUP → PREPARE_CHILD
                 ├─ invalid / unavailable / serializer failure → STOCK_RESPONSE
                 └─ listener LISTENING + child prepared + serializer success
                      → CHILD_ACTIVE
                           ├─ child teardown → PARENT_ACTIVE
                           └─ parent teardown → CLOSED (all owned resources closed)
```

No transition in this diagram means an Apple acceptance, genuine Honda
receiver call, Type111 authentication, or Display 1 handoff.

## Prior-art review and separation

The source-pinned comparison records these projects as architecture references,
not Honda evidence:

- [MIB2Q CarPlay RGI, GPL-3.0](https://github.com/luka-dev/mib2q-carplay-rgi/tree/9861081888103dbe2455c763524e9f5344e8844c)
  describes an Audi MHI2Q cluster integration. Its source-pinned AltScreen
  overview separates display/feature negotiation, Type111 SETUP, bounded frame
  forwarding, decode, presentation, and reconnection. Its hardware claims are
  author/project claims for supported Audi profiles, not independently
  reproduced here. See its [AltScreen/video overview](https://github.com/luka-dev/mib2q-carplay-rgi/blob/9861081888103dbe2455c763524e9f5344e8844c/docs/altscreen-and-video/README.md)
  and [architecture map](https://github.com/luka-dev/mib2q-carplay-rgi/blob/9861081888103dbe2455c763524e9f5344e8844c/docs/reference/ARCHITECTURE.md).
- [MHI2 AltScreen CarPlay, GPL-3.0](https://github.com/harman-f/mhi2_altscreen_carplay/tree/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c)
  is open research for VW-group MHI2 systems. The source-pinned review records
  separate sender stream lifecycle, UI selection, ViewArea state, and listener
  ownership; these inform separate modeling of transport and presentation but
  do not establish Honda messages or ownership. A newer repository head was
  observed during campaign preparation; the technical claims here remain tied
  to the analyzed revision.
- [xcertplay, GPL-3.0](https://github.com/shilapi/xcertplay/tree/1298fb35e29ee30e7bd849cb0e751b52aa22a13f)
  has source-level alternate-display descriptors and Type111 SETUP gated by
  negotiated AltScreen/UI-context state. Its source contains its own listener,
  stream, decoder, and teardown choices. Its source analysis is not an
  independently verified current iPhone/Honda result.

The implementation adopts only general separation principles: explicit
negotiation gates, one child per parent generation, independent listener
ownership, readiness before response, stock fallback, and stale-generation
rejection. It does not copy GPL implementation code, assume `altScreen`,
`enabledFeatures`, `displayPanels`, `extendedFeatures`, or ViewArea keys are
Honda wire contracts, or reuse another project's stream-security assumptions.
Existing source-pinned detail and provenance remain in
[`carplay-altscreen-prior-art.md`](../research/carplay-altscreen-prior-art.md),
[`type111-implementation-comparison.md`](../research/references/type111-implementation-comparison.md),
and [`type111-security-and-licensing.md`](../research/references/type111-security-and-licensing.md).

## Acceptance

`tests/jmcs/test_cl_t111_lab_model.py` exercises stock-only mode, complete and
incomplete readiness, both setup orders, listener failure after candidate
creation, absent/wrong parent identity, malformed and oversized requests,
serializer failure, disconnect during preparation, duplicate SETUP, child vs
parent teardown, rapid reconnect, Type110 response equivalence, and resource
cleanup. These are deterministic unit/integration model results only.

Future Honda-native prerequisites remain unproven: genuine `/info` caller
execution, receiver-created session identity and Screen association, actual
listener/security ownership, Type111 setup acceptance, factory Display 1
handoff, and warning/recovery behavior. The protocol declaration is not a
native acceptance gate or authorization to connect to a vehicle.
