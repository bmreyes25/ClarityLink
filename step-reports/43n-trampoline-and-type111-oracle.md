# Step 43N — trampoline model and Type111 oracle evidence (offline)

**Base:** `0a749a09f574834a8743beb590ac177798ed5010` (`ClarityLink: close Honda post-Setup wrapper seam`). Initial state was clean `main`, synchronized with `origin/main`. The Honda binary hash matched `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

**Boundaries honored:** no Honda runtime, vehicle, ADB, patching, deployment, phone connection, live listener, private credential/key, or patched binary. The pinned GPL projects were inspected in filtered temporary checkouts only; no source was copied or vendored.

## Honda callsite re-verification

At `_connectionHandleMessage` (`0x28a30c`, Thumb), callsite `0x28afba` contains bytes `fe f7 d1 ff` and decodes as Thumb-2 BL from PC `0x28afbe` with displacement `-0x105e` to `_requestSendPlistResponse` at `0x289f60`. The original call's LR is `0x28afbf` (Thumb-tagged); its continuation instruction starts at `0x28afbe`.

The caller prologue pushes nine words (36 bytes: r4-r11 and LR), then subtracts `0x2b4` (692 bytes), total frame delta `0x2d8` (728 bytes). Under AAPCS32's 8-byte-aligned function-entry SP, the callsite SP remains 8-byte aligned. The inspected argument staging immediately before BL is:

| Register/state | Meaning at callsite |
|---|---|
| `r0` | HTTP connection (`r4`) |
| `r1` | HTTP request/message (`r6`) |
| `r2` | exact Setup response (`[sp+0x54]`) |
| `r3` | pointer to `statusOut` (`sp+0x50`) |
| `[sp+0x1c]` | parsed Setup request dictionary |
| `[r10+0xf4]` | receiver/session pointer |
| `r4-r11` | AAPCS callee-saved values; connection/message/context include live transaction state |
| `r12` / flags | caller-saved; the immediate continuation does not consume flags |

The callsite-context bytes at `0x28afb2` are `31 46 20 46 15 9a 14 ab fe f7 d1 ff 06 46 40 e0`, SHA-256 `edec335f1cd6f9d0d053a0d2b4a05f515c25e1a1524fccca2c4c0ebd610273df`. The caller prologue fingerprint at `0x28a30c` is `df f8 8c 24 2d e9 f0 4f 04 46 df f8`, SHA-256 `be9f272a09201f326e42c27962609add81149bbe1adb9e843bb8b8ff685d7878`.

## Offline stock-delegating trampoline model

Added `src/claritylink-negotiation/trampoline_contract.py` and expanded `tools/jmcs_integration/callsite_plan.py`.

The conceptual flow is:

```text
callsite BL -> project adapter (entry LR saves 0x28afbf)
  bounded prepare, preserving args and caller state
  restore original r0-r3; BL original serializer exactly once
      serializer LR points back into adapter
  capture stock r0 and statusOut
  bounded post/commit-or-rollback using exact generation
  restore saved caller LR and SP; return stock r0 at 0x28afbe
```

The stock serializer must have an adapter-local LR to return for post-processing; this necessarily differs from the original direct-call LR `0x28afbf`. Its hash-matched prologue saves LR for an ordinary return, and no return-address inspection was found in the bounded function. This narrows the compatibility concern but does not prove runtime compatibility. The model restores original serializer arguments and caller LR, preserves `r4-r11` and SP, calls stock once even if project prepare fails, and makes post-processing read `statusOut` by value so the project cannot rewrite it. It preserves Honda's serializer `r0` exactly. APSR flags and `r12` are not promised after the call because the observed continuation does not rely on them and they are caller-saved.

The modeled commit predicate is the existing Honda predicate `r0 == 0xc8 && statusOut == 0`; it means local serialization/body installation success, not phone receipt. Generation remains project-owned and authoritative for stale cleanup. The model and tests are `OFFLINE_PROJECT_IMPLEMENTATION` / `SYNTHETIC_TEST_VALUE`, not executable Honda hook code.

The planner validates the whole SHA-256, ARM32 ELF class/machine/type, Thumb call bytes, decoded destination, callsite context bytes/hash, caller prologue bytes/hash, and continuation. Any mismatch rejects. It emits only a JSON plan; patch bytes are `NOT_EMITTED`, runtime attachment is `NOT_IMPLEMENTED`.

Thumb-2 BL uses PC `call+4`, signed displacement `-0x1000000..+0xfffffe`, halfword alignment. For the low Honda VA, the negative range boundary is below address zero; address zero itself remains directly reachable. Upper edge `0x128afbc` is reachable and `0x128afbe` is not. Out-of-range requires a validated veneer; an ARM-state target requires a separately validated interworking veneer. Only the existing four-byte BL is in scope; no arbitrary prologue relocation or second displaced instruction is assumed.

## Pinned external source audit

| Project | Pinned evidence | Result |
|---|---|---|
| DiPlay | `shihabal3amri/DiPlay` commit `f2d06951b4e8114dbb62f551c12a32a845a3042f`, “Prepare DiPlay 0.2.8 release”; selected info/session/cluster/media/screen files and `docs/BYD_NAVIGATION.md` | **EXTERNAL_PRIOR_ART:** optional second display 111, `altScreenURLs`, initial URL, `viewAreas`/`safeArea`, `viewAreas`/`altScreen` Setup feature negotiation, independent stream 111 listener/dataPort, UUID-scoped `forceKeyFrame`/`showUI`/`stopUI`. **EXTERNAL_PHYSICAL_VALIDATION:** pinned docs report Apple Maps/iOS 27 cluster map on DiLink 5.0/Android 12; maintainer-published, not independently reproduced. |
| PlayPort | `youcci/playport` commit `9a0882dd0ffe48e467b59d58b12d81391df55ade`, “Refresh README screenshots with live CarPlay”; protocol, server and web paths inspected | **EXTERNAL_PRIOR_ART:** supports 110/111 setup, per-stream keying and stream-type-bearing web wire messages. Default `CarPlayServer` config omits cluster; current browser app routes all video to one player/canvas. It is a promising lab base, not a ready dual-canvas oracle. |
| Existing refs | xcertplay `de9647f4bdfb1be356bed4cac0519400473712a6`; MHI2 `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c` | Retained as separately pinned external prior art; no target-specific behavior transferred to Honda. |

The detailed source map is in the [DiPlay differential](../research/carplay/diplay-type111-differential.md) and [PlayPort differential](../research/carplay/playport-type111-differential.md). Source was not copied into ClarityLink.

## Crypto boundary

The pinned DiPlay/PlayPort screen path derives DataStream output keys from authenticated session shared secret plus `streamConnectionID` with DataStream HKDF labels and uses ChaCha20-Poly1305 for frame bodies. Honda Type110 is `HONDA_CONFIRMED` to use its legacy SHA-512 key/IV derivation and continuous AES-CTR body protection. Honda Type111 remains `HONDA_UNKNOWN`. A 128-byte header-family resemblance does not establish cipher, key, or nonce compatibility. See [security differential](../research/carplay/honda-vs-modern-type111-security.md).

## Honda response implication

The current `0x28afba` candidate could only affect the successful Setup response before serialization. If external evidence fields ever prove necessary, do not place them in Honda by default. A second display advertisement would have to be added earlier in Honda's `/info` path; `enabledFeatures` and a Type111 Setup response entry, if validated, belong in the distinct Setup response transaction. Preserve the same Honda response object, Type110 entry, and stock audio state, and keep any Type111 stream/resource state project-owned. Phone-validity and Honda Type111 security are not established by the external sources.

## PlayPort oracle design

[The lab plan](../research/lab/playport-type111-oracle-plan.md) scopes an isolated opt-in cluster config and independent 110/111 browser players, with tightly redacted diagnostics for only `altScreenURLs`, proposed features, selected stream keys/dataPort, media type, and UUID-class control events. It explicitly avoids complete authentication dumps and any private-key handling. This is a design only; no iPhone connected during 43N. Any phone/credential use requires a separate milestone authorization.

## Decision table

| Field | Result |
|---|---|
| HONDA BINARY | Exact reference SHA matched |
| CALLSITE | `_connectionHandleMessage` `0x28afba` |
| ORIGINAL SERIALIZER | `_requestSendPlistResponse` `0x289f60` |
| CALLSITE BYTES | `fe f7 d1 ff` |
| THUMB MODE | Thumb-2 BL; PC `0x28afbe` |
| CONTINUATION | `0x28afbe` (Thumb function pointer `0x28afbf`) |
| LR MODEL | Adapter entry saves `0x28afbf`; serializer returns to adapter with adapter-local LR; adapter restores original continuation |
| STACK ALIGNMENT | Frame delta `0x2d8`; callsite SP stays 8-byte aligned under AAPCS entry alignment |
| REGISTER PRESERVATION | restore original `r0-r3` for serializer, preserve `r4-r11` and SP, return stock `r0`; statusOut is read-only post-call; flags/r12 caller-saved |
| HASH GATE | Full reference SHA-256 exact match required |
| BYTE GATE | Target BL, surrounding context, caller prologue exact match required |
| TRAMPOLINE MODEL | `READY_OFFLINE`; synthetic control-flow contract only |
| ORIGINAL CALLED EXACTLY ONCE | Yes in every modeled non-throwing stock path |
| DIPLAY PIN | `f2d06951b4e8114dbb62f551c12a32a845a3042f`, pinned message confirmed |
| DIPLAY PHYSICAL TYPE111 EVIDENCE | Pinned maintainer docs report DiLink 5.0 / Android 12 + iOS 27 Apple Maps cluster-map test (`EXTERNAL_PHYSICAL_VALIDATION`) |
| ALTSCREENURLS | Three documented Maps URL family values; app/iOS-dependent (`EXTERNAL_PRIOR_ART`) |
| SECOND DISPLAY STRUCTURE | Optional type 111, independent UUID, no cluster input, dimensions, viewAreas/safeArea, initial URL (`EXTERNAL_PRIOR_ART`) |
| INITIALURL | Maps instrument-cluster map used; absent URL reported black frame in tested setup (`EXTERNAL_PRIOR_ART`) |
| ENABLED FEATURES | `viewAreas`; `altScreen` when cluster configured (`EXTERNAL_PRIOR_ART`) |
| TYPE111 SETUP RESPONSE | Separate accepted `{type:111,dataPort}` (`EXTERNAL_PRIOR_ART`) |
| TYPE111 DATAPORT | Per-stream listener port, model only; ClarityLink test port synthetic |
| ALT KEYFRAME COMMAND | `forceKeyFrame` scoped by AltScreen UUID (`EXTERNAL_PRIOR_ART`) |
| SHOWUI/STOPUI | UUID-scoped external commands; stream remains up (`EXTERNAL_PRIOR_ART`) |
| DIPLAY CRYPTO PORTABLE TO HONDA | No; Honda Type111 security remains `HONDA_UNKNOWN` |
| PLAYPORT PIN | `9a0882dd0ffe48e467b59d58b12d81391df55ade`, pinned message confirmed |
| PLAYPORT TYPE111 PROTOCOL SUPPORT | Yes, separate 110/111 setup/media types; type reaches Web wire |
| PLAYPORT DEFAULT CLUSTER ENABLED | No |
| PLAYPORT MAC ORACLE FEASIBLE | Design feasible after opt-in cluster and dual-canvas changes; no live test in 43N |
| HONDA TYPE110 PRESERVED | Synthetic transaction tests preserve stock Type110 data; no Honda runtime test |
| HONDA AUDIO PRESERVED | Synthetic transaction tests preserve stock audio state; no Honda runtime test |
| HONDA TYPE111 SCHEMA READY | No; external fields are not Honda fields |
| HONDA TYPE111 CRYPTO READY | No; `HONDA_UNKNOWN` |
| JMCS ATTACHMENT DESIGN | `DESIGNED_NOT_DEPLOYED` |
| LIVE HONDA TEST READY | No |
| MAC/IPHONE ORACLE TEST READY | Design ready; implementation and separately authorized phone run remain |
| LD_PRELOAD | PARKED |

## Verification and readiness

- Full configured suite: **299 passed, 4 skipped**. The four skipped tests require ignored/private capture fixtures and are excluded by the repository runner.
- Focused Setup, response delivery, lifecycle, trampoline, target planner, external provenance, and transaction tests: **85 passed**.
- Self-locator standard-library smoke: **3 passed**. Simulator contract adapter, dual-screen model, guidance expiry, and Type111 failure-twin checks all passed.
- `git diff --check`: **PASS**.
- ECC research/terminal workflows were applied; no dedicated ECC review service was available, so review checklists were applied manually. Honda runtime, iPhone, vehicle, Type111 live, and ExternalDisplay tests remain NOT READY.
