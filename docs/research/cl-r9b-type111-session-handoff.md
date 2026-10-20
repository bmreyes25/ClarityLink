# CL-R9B — Type111 SETUP and authenticated session handoff

**Decision scope:** offline source/static review and synthetic tests. No Honda or iPhone operation, ADB, firmware/binary patch, credential extraction, or authentication implementation. `safeForHonda()` remains `false`.

Evidence classes used below: `STATIC_HONDA_EVIDENCE` is bounded static analysis of the reviewed Honda paths; `AUDI_REFERENCE_ONLY` is evidence about the Audi implementation; `SYNTHETIC_TEST_VALUE` is offline model behavior; `UNKNOWN` is unresolved. No `VERIFIED_HONDA_CONTRACT` exists for Type111 delegation.

## Decisive assessment

For the reviewed Honda `jmcs` paths, the factory receiver does not have a recovered Type111 SETUP branch: it dispatches Type110 and logs/skips unsupported Type111. No supported receiver-to-consumer handoff for a Honda-authorized Type111 stream was found. The post-SETUP response interval is a structural static candidate, not an approved extension API. The project must not synthesize an authorization proof from a parseable request or response.

The ClarityLink Type111 listener/decoder/renderer chain is technically usable in its synthetic and authorized-lab models. It is **not integrated with Honda** because Honda Type111 admission, Type111 cryptographic context, and an authorized stream-consumer interface are missing. The Type110 primary path remains separately owned; the mock delegation model's parent-revocation behavior was corrected to stop both child and parent-owned synthetic screen state.

## Type111 ownership map

```mermaid
sequenceDiagram
  participant Phone
  participant Honda as Honda jmcs (reviewed static path)
  participant Auth as Honda session/auth owner
  participant CL as ClarityLink Type111 pipeline
  participant Render as ClarityLink display sink
  Phone->>Honda: SETUP streams[]
  Honda->>Auth: existing factory session owns auth material
  Honda->>Honda: dispatch Type110; unsupported Type111 is skipped
  Note over Honda,CL: No supported Type111 handoff edge recovered
  CL--xHonda: No real Honda adapter; Type111 request fails closed
  Note over Auth,CL: Session security context must stay with Auth
  CL->>CL: synthetic/lab-owned listener, generation, parser, decoder
  CL->>Render: decoded Type111 frame
```

The first four edges reflect bounded static Honda observations. The synthetic/lab pipeline shown below the boundary is not a Honda execution path. Dashed/red rejection is intentional: a parsed descriptor cannot grant stream authority.

## Audi implementation: observed behavior versus target details

Reference inspected at upstream HEAD `71b4ab1c9461d5383a7aa6d56d4dda34f567ade7`: [altscreen_hook.c](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/hook/altscreen/altscreen_hook.c), [altscreen_av.c](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/hook/altscreen/altscreen_av.c), [altscreen_av.h](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/hook/altscreen/altscreen_av.h), [airplay_seams.c](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/hook/framework/airplay_seams.c), and [protocol.h](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/altscreen_render/protocol.h). Relevant source-backed documents are [AltScreen Cluster Video](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/docs/altscreen-and-video/ALTSCREEN_CLUSTER_VIDEO.md), [AltScreen RE History](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/docs/altscreen-and-video/ALTSCREEN_RE_HISTORY.md), and [CarPlay Feature Survey](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/docs/altscreen-and-video/CARPLAY_FEATURE_SURVEY.md).

| Finding | Classification |
|---|---|
| The SETUP callback scans the request `streams[]` for `type == 111`. It reads the selected descriptor's `streamConnectionID`; the stock MHI2 Setup handles 100/101/110 and skips 111. | Direct Audi source behavior, target-specific implementation. |
| The hook creates a TCP listener, appends `{type:111, dataPort:<bound port>}` to the Setup response, and starts its acceptor before publishing the response entry. Setup failure propagates an error and rolls back the hook-owned receiver. | Direct Audi source behavior; response schema is Audi implementation, not Honda protocol proof. |
| The wired path derives AES key/IV using the stock session's AES session key and the requested connection ID. A separate conditional wireless/QEMU path claims fresh paired-session key material. The hook itself owns receive/decrypt; it does not create a stock Screen/ScreenStream object for 111. | Audi implementation detail. Session offsets, key derivation, QNX socket calls and wireless key claim are not portable Honda interfaces. |
| The receiver consumes a 128-byte stream header. Opcode 1 carries unencrypted avcC configuration; opcode 0 carries encrypted AVCC access units; other handled/ignored opcodes and checks are in the hook. It decrypts, parses, converts length-prefixed NAL units to Annex-B, and forwards to a separate renderer over localhost TCP. | Audi implementation observation; framing, opcodes, crypto and endpoint are not a Honda contract. |
| `altscreen_av.c` owns a bounded queue and a single renderer transport/config owner. A strictly newer generation can claim it; stale generations cannot forward, replace config, or close the new owner's socket. Queue loss fences dependent frames and waits for configuration plus IDR. | `AUDI_REFERENCE_ONLY`. Mutexes, QNX constraints and local process protocol are target-specific. |
| Cached SPS/PPS is replayed before a fresh connection's IDR. Identical avcC does not reset a running decoder; changed config closes the current renderer connection and reconnects at a subsequent IDR. | Audi VideoConfig lifecycle behavior, not Honda validation or acceptance. |
| Per-stream teardown only stops the Audi receiver if the teardown request contains Type111; full parent session teardown retires all session generations. Reconnection retires prior slots by session pointer, advances receiver/transport generations, and defers joins/GC for still-running threads. | Audi hook lifecycle behavior. Thread ownership and QNX socket close timing are implementation details. |
| Setup sequencing, phone's Type111 selection, UUID-to-stream rules and feature gates described as verified iOS 26.6 behavior. | Audi authors' reverse-engineering reports. Not independently verified here and not universal across iOS versions or Honda. |

No Audi LD_PRELOAD hook, QNX code, structure offset, transport key, or wire implementation was ported.

Race/renderer details are source-level Audi behavior: the hook publishes its global target session/generation under `alt_lock` only after listener/acceptor setup and response-entry construction; the renderer forwarder checks ownership under its transport mutex. Renderer protocol uses bounded messages (`ALTAV_MAX_MSG` is 4 MiB), legacy length-prefixed payload or negotiated 40-byte metadata records, and a separate control connection. These locking, queue, port, record and process boundaries are Audi design details, not Honda API requirements.

## Honda evidence and handoff contract status

| Contract element | Honda static observation | Classification/status |
|---|---|---|
| Parent session authority | Honda's factory session and delegate callbacks own the authenticated receiver lifecycle. `AirPlayReceiverSessionSetup` receives the Honda session. | `STATIC_HONDA_EVIDENCE`; no consumer handoff. |
| Type111 admission | The reviewed SETUP dispatcher reads `streams[].type`; Type110 enters the screen branch; unsupported values including 111 are logged/skipped in the examined path. | `STATIC_HONDA_EVIDENCE`; cannot say factory legitimately creates Type111. |
| Stream connection identity | Type110 reads a nonzero uint64 `streamConnectionID`; it feeds the existing Honda screen key/IV derivation with receiver-session master material. A persistent named field or display-UUID correlation is not recovered. | `STATIC_HONDA_EVIDENCE` for Type110 only; Type111 meaning/reuse `UNKNOWN`. |
| Factory authentication ownership | The stock receiver's master/session state is consumed within the Honda path. No supported export, reference, or per-stream derived-context API was identified. | `STATIC_HONDA_EVIDENCE`; no safe context transfer. |
| Transport interface | Honda's listener and screen path serve the known primary stream. No Type111 listener, response port, transport owner, or Type111-to-decoder edge was recovered. | `STATIC_HONDA_EVIDENCE`; Type111 transport `UNKNOWN`. |
| VideoConfig | ClarityLink has a bounded parser for fields recovered from the Honda helper, and an existing synthetic Type111 receiver pipeline. Honda's Type111 avcC delivery/order and accepted configuration lifecycle are not known. | `STATIC_HONDA_EVIDENCE` plus `SYNTHETIC_TEST_VALUE`; not an authorized handoff. |
| Post-SETUP integration window | The same stock response reaches the synchronous serializer after Setup. The candidate window exists after stock success and before serialization. Arbitrary callout safety, mutation races, and rollback of all side effects are not proven. | `STATIC_HONDA_EVIDENCE` for caller dataflow; implementation readiness remains NO. |
| Parent teardown subscription | The per-session delegate is a whole-record Honda-owned table. The global interface callback is a replacement slot without the AirPlay session argument. No chainable subscriber carrying session identity was found in the reviewed search. | `STATIC_HONDA_EVIDENCE`; not a supported project-child cleanup hook. |
| Actual receiver-to-consumer handoff | No versioned Honda specification or documented API authorizes ClarityLink to receive Type111 bytes or consume Honda session security state. | `UNKNOWN` / none found; no Honda adapter. |

### Required handoff contract, if Honda provides one

This is a specification checklist, **not an implemented Honda adapter**:

1. A documented parent-session authority must authenticate and retain the parent. Every handoff is bound to that opaque session identity and exact parent generation; session keys and security context stay owned by that authority.
2. The same authority must explicitly authorize one Type111 stream for a verified request/stream connection ID. A parsed request, `type=111` string, display descriptor or model token is not authorization.
3. The authority supplies supported transport-security metadata or a secure receiver-owned channel. ClarityLink must not derive or guess keys, copy Honda secrets, downgrade to clear, or take ownership of the authentication context.
4. Stream generation is distinct from parent generation. Duplicate setup, stale callbacks, wrong session/connection/type, or incomplete metadata reject before publishing decoder/listener state.
5. A VideoConfig is accepted and validated before forwarding dependent media. Parser, config, queue, listener, decoder and renderer are bounded and owned by that exact stream generation.
6. Stream withdrawal closes only Type111 resources. Type110 stream disconnect and Type111 failure leave factory Type110/audio/control ownership intact; parent-owner loss revokes every child and all parent-bound work.
7. Partial setup is transactional: prepare resources privately, publish only after all required authority/config/transport stages succeed, and rollback project-owned state on any failure. The Honda serializer's error path is not presumed to retry or deliver stock Type110.

Concrete candidate boundary: a Honda-documented **receiver-owned Type111 stream delegate** that returns a narrowly scoped, opaque, generation-bound transport handle and teardown notifications; ClarityLink's existing receive/security/VideoConfig/decoder interfaces consume only that handle. A safe alternative is a documented authorized local IPC stream relay. The current post-SETUP response mutation seam is not sufficient by itself: it returns metadata control, not authenticated media ownership, security context, or reliable lifecycle callbacks.

## Feasibility answers

**A. Can the factory receiver legitimately create a Type111 stream?** Not established for the reviewed Honda artifact. Its recovered branch skips Type111. A new authorized Honda specification or implementation proof is required.

**B. Can it authorize an external or internal consumer?** No supported authorization/handoff interface was found. Honda's internal authority remains Honda-owned; seeing its session pointer or response dictionary is not permission to consume media.

**C. Can ClarityLink's existing decoder receive the data under supported ownership rules?** It accepts synthetic/lab-owned Type111 input. Honda-origin Type111 cannot reach it under a proven supported ownership/security contract today.

**D. Does the proposed design preserve Type110?** The *separate-child design* can preserve Type110 by leaving factory stream state untouched and owning only a Type111 child. The offline model tests that invariant. This is feasibility of the model, not completed Honda integration or runtime proof.

**E. What specification is missing?** Honda's supported Type111 admission and response schema; connection-ID meaning and mapping; authorized stream-consumer API; transport endpoint/framing and security metadata/key scope/CTR lifecycle; accepted VideoConfig timing/format; stream and parent teardown callbacks; and partial-failure/reconnect behavior. Also missing is evidence the target phone requests Type111 under that Honda contract.

**F. Is an independent receiver relevant, and what authority would it need?** Technically, an independent receiver could keep Type110 untouched and own a separate Type111 pipeline. It still needs its own legitimate Apple-compliant accessory authentication/session authority, or a Honda-documented authorized delegation of a scoped Type111 transport/context. An independently parsed request, copied master key, guessed KDF, or synthetic token cannot supply that authority.

## Offline implementation and tests

`StockFirstType111Delegator` remains explicitly a mock primary session plus the existing offline Type111 setup contract. This change fixes parent revocation so it destroys both the modeled Type111 child and its parent-owned Type110 screen state. Its stream teardown helper is explicitly model-only: Type110-only teardown does not retire the Type111 child; Type111 teardown does; parent revocation stops both.

New fixtures exercise both request orders, mock-owner authorization/rejection, wrong parent generation, Type111 rejection by the disabled Honda static adapter, wrong type and duplicate Type110 connection ID, missing/invalid connection metadata, duplicate SETUP, unavailable listener allocation, Type111 disconnect, Type110-only teardown, parent-owner death, and partial listener/serializer failure rollback. The separate existing R7 integrated receiver tests exercise actual ClarityLink lab receiver setup orders and are run as regressions. All authority in these tests is plainly synthetic; tests do not authorize Honda. Listener-allocation failure tests only ClarityLink's project-owned listener preparation, not Honda authorization or transport delegation.

## Exact next evidence

Obtain from Honda or its authorized integrator an applicable model/version specification and an explicitly supported API/IPC for a same-session Type111 stream handoff. It must state how the factory session authorizes the consumer without exporting parent credentials; bind parent/session generation and stream connection ID; define Type111 response/transport and security metadata; define VideoConfig/media framing; define stream withdrawal, parent death, reconnect and rollback; and preserve existing Type110/audio/control ownership. If no such API exists, a distinct receiver requires its own approved Apple-compliant authentication authority and supported transport authorization. No further inference from the Audi implementation or current Honda Type110 behavior can close this gap.
