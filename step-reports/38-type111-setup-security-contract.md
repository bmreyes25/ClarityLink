# Step 38 — close Type111 Setup and security contract

**Date:** 2026-09-29
**Starting commit:** `255c8e7`
**Scope:** offline static analysis of the identity-verified Honda `jmcs` ELF, pinned MHI2 source comparison, synthetic Setup/KDF/lifecycle models. No vehicle, ADB, ptrace, firmware modification, live hook/listener, or real/session keys.

## Evidence identity and method

Honda ELF: `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

Disassembled full `AirPlayReceiverSessionSetup` at `0x2854e0` through its epilogue, `AirPlayReceiverSessionTearDown` at `0x2852ec`, `_AddResponseStream` at `0x284db8`, response caller/serializer, `_ScreenTearDown` at `0x284628`, Type110 KDF at `0x288d18`, SHA512 helper at `0x288c6c`, and `AirPlayReceiverSessionScreen_SetSecurityInfo` at `0x287d28`. DWARF formal parameters were inspected for both KDF functions. Honda evidence is authoritative; pinned MHI2 source was fetched to `/tmp` for read-only comparison and is not part of the repository.

## Honda Setup state machine and final result

Setup creates its mutable output response and initializes an error/status slot before the stream list. It gets typed `streams[]`, count and index, then dispatches each dictionary's integer `type`:

```text
create mutable response; status = 0
prepare common receiver/control state
streams = typed request array; count; i = 0
while i < count:
    entry = typed dictionary streams[i]
    if status != 0: go to error cleanup
    type = CFDictionaryGetInt64(entry, "type")
    if type == 100 or 101: run audio setup; setup error => cleanup/abort
    elif type == 110: run screen setup; setup error => cleanup/abort
    else:
        LogPrintF(unsupported type)     # 0x2861f6
        # no status write, response edit, or session mutation
    i += 1                              # 0x286220
    continue if i < count
status = AirPlayReceiverSessionPlatformControl(...)
if status == 0: *outResponse = response   # 0x286260
else: release response; teardown request/session
return status
```

The default branch's only semantic action is logging. It cannot cause rollback itself. Therefore the exact classification is **CONDITIONAL success**: for `[100,110,111]` or another ordering, if every recognized stream handler and post-loop `PlatformControl` return success, Setup returns success. Type111 contributes no stock response. The HTTP caller only serializes on the successful OSStatus; this does not prove the phone accepts an augmented response.

The same reasoning covers Type111 before/after valid streams. Position of Type111 does not affect supported handling or error status. Other ordering and duplicate constraints among supported entries remain separate and can affect processing.

## Response entries, mutability, and preservation

`_AddResponseStream` gets the response `streams` array. If absent it creates a `CFMutableArray`, appends the new entry, sets it on the mutable response dictionary, and releases its local array reference. If present it appends to that array. The Type110 builder creates `type=110`, inserts the allocated `dataPort`, and appends. A later unsupported 111 branch leaves the array intact. Setup's output is the same +1 CF response object serialized synchronously by `_requestSendPlistResponse`; caller releases it after serialization.

**Valid stock response preservation: YES, on non-error path.** An existing Type110 response entry remains when unsupported Type111 is later encountered; when 111 comes first, it does not prevent Type110's subsequent entry. There is no Type111-triggered response clear.

The response is structurally appendable after Setup and before synchronous serialization. The CF ownership pattern for new code is: create descriptor +1; append (array retains); store copied/replaced streams array (response retains); release local references; retain caller-owned response ownership. If allocation/copy/append fails, release temporaries and any project resources, then return untouched stock response.

## Rollback and stream order

Unsupported Type111: **NONE**. It is not written into the Setup error slot and does not invoke cleanup.

A different recognized-stream failure follows a real error path. Type110 failure can run `_ScreenTearDown`; audio/stream errors use `_TearDownStream`; Setup then invokes `AirPlayReceiverSessionTearDown` with the original request/status and does not return the successful response. This is not caused by an unsupported stream.

Partial teardown is supported for Honda's recognized types: `AirPlayReceiverSessionTearDown` reads a supplied streams list, routes 100/101 through `_TearDownStream`, 110 through `_ScreenTearDown` and screen stop cleanup, and logs/skips unknown 111. Unknown Type111 does not acquire a project listener in Honda and cannot clean a ClarityLink-owned one. A separate project teardown path is required.

`_ScreenTearDown` signals/joins its screen worker, closes the screen listener descriptor, clears it, and clears the started flag. `AirPlayReceiverSessionTearDown` also performs full-session cleanup when no partial stream list path applies. This is Honda Type110 lifecycle evidence only.

## Delegation decision: original request

Choose **STOCK-ORIGINAL**: pass the original mixed request to Honda once, preserve stock response, then prepare and append project output only after stock success. Honda's default branch is statically a no-error skip. Filtered clone, split arrays, or dispatcher interception would modify stock request semantics and add ownership/ABI risk without evidence they are needed.

If Honda Setup fails, do not create Type111 resources. If project crypto/listener preparation fails, return the stock response unchanged and clean partial project state. If augmentation fails, close project state immediately and return the stock response. For serialization failure, Step39 needs to connect error observation or session teardown to project cleanup; the Setup hook alone does not prove that edge.

## Descriptor and response schema

Honda parses generic `type`; Type110 additionally requires nonzero `streamConnectionID` as uint64 for security derivation. No Honda Type111 code reads its descriptor, so `streamConnectionID` presence/requirements for Type111 are **prior-art only**. Treat only `type` and a validated connection ID as fields to parse; preserve all other request keys opaquely.

Actual pinned MHI2 source `src/native/altscreen111-gen2/libaltscreen111_gen2.c` at commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c` scans type 111, reads `streamConnectionID`, clones the entire descriptor, and appends a response clone with `dataPort` and `streamID=111`. Its `mibr_session_setup` calls stock with the original request before scanning/augmenting. Its `clone_without_111` helper is in the teardown path, not Setup. This source evidence corrects prior local Step34 wording that claimed filtered stock Setup.

Honda's only established response shape is `{type:110, dataPort}`. Type111's identity field spelling and full schema remain unknown. The offline augmenter uses the MHI2 clone-plus-`streamID=111` structure explicitly as prior-art model, not Honda-confirmed protocol.

## Type110 KDF ABI

`AirPlay_DeriveAESKeySHA512ForScreen` DWARF signature inputs: pointer to master material, length, uint64 ID, key output pointer, IV output pointer. The Type110 caller supplies `session+0x1b8`, length 16, connection ID in `r2:r3`, and 16-byte stack output buffers.

The helper creates key and IV salts with exact format `%s%llu` and prefixes `AirPlayStreamKey` / `AirPlayStreamIV`. The uint64 becomes unsigned decimal ASCII (not network-order raw bytes). `AirPlay_DeriveAESKeySHA512` independently computes SHA512(salt || master material) for each and copies the first 16 digest bytes to the output. Setup passes them to `AirPlayReceiverSessionScreen_SetSecurityInfo`, which calls `AES_CTR_Init` on the screen object's `+0xc8` context, finalizing a prior context first. Temporary salt strings and Setup key/IV buffers are wiped after use.

The stream type is not passed to KDF and is not consulted by the recovered decrypt/framing path after dispatch. The Honda screen context belongs to one screen object/stream and maintains one continuous CTR state. Type111 needs an independent CTR state. MHI2 uses the same stock derivation model for its separate Type111 context; Honda Type111 compatibility remains unknown.

## Lifecycle, generation and session start

Type110 Setup installs screen crypto and creates its listener before Setup response serialization. It may call `_ScreenStart` depending on the receiver session's start flag. MHI2 attaches its private Type111 state after stock SessionStart succeeds. The host model prepares project state before advertising the response and treats connection ID/new Setup as a new generation, clearing old socket/parser/config/CTR ownership.

For Type111, project teardown must close listener and accepted socket, clear key/IV/CTR and partial frame/config state, clear connection ID/port, and transition the generation once. Honda's type111 teardown path is absent. Whether phone uses partial Type111 teardown is prior-art/unknown for Honda; do not tie Honda Type110 teardown to the project stream without further lifecycle proof.

## Capability/request gate and two-hook sufficiency

Honda Setup proves that if a Type111 request arrives mixed with supported streams, stock will skip that entry and still finish conditionally. It does not prove what phone-facing capability fields cause an iPhone to send Type111, whether one additional display descriptor is sufficient, or whether the iPhone accepts the cloned MHI2-shaped response. The exact MHI2 source adds root enabledFeatures values altScreen and viewAreas on successful Setup response, and clones the Type111 request descriptor; these are target-specific prior-art behaviors.

Two hooks (/info descriptor augmentation plus post-Setup response augmentation) are therefore **UNKNOWN** for first TCP accept. The single unresolved gate is the iPhone Type111 request/response trigger contract: which advertised secondary-display/capability fields cause the request, and which response identity fields make the phone connect. This does not block continuing Step39 offline.

Honda main display descriptor fields include uuid, features, maxFPS, pixel and physical dimensions, and EDID. The correct ClusterDisplay UUID, features, EDID and geometry are not available from this transport analysis; do not copy or fabricate them as final values.

## Offline implementation

Added under `src/claritylink-negotiation/`:

- `setup_augmentor.py`: validates a single nonzero uint64 Type111 request, copies stock response and descriptor, preserves opaque fields/order, and appends MHI2-shaped prior-art response fields.
- `setup_transaction.py`: injected stock-first/project-prepare/rollback transaction. Stock failure skips project setup; project setup or merge failure returns a stock response copy and rolls back.
- `screen_kdf.py`: exact Type110 SHA512 derivation contract with synthetic-only key inputs.
- `lifecycle.py`: deterministic generation/state model; no sockets or secrets.
- `tests/negotiation/test_setup_contract.py`: mixed/stock-only ordering, opaque preservation, duplicate/missing/invalid ID, malformed response, stock failure, project/merge rollback, KDF vector, and lifecycle generation tests.

The module does not open a listener, invoke Honda, or claim Honda Type111 schema/security compatibility.

## Readiness gate

| Component | Result |
|---|---|
| Honda Type111 loop action | CONTINUE |
| Overall Honda Setup with 111 | CONDITIONAL success on supported branches and final PlatformControl |
| Existing valid stock responses survive 111 | YES |
| Rollback caused by 111 | NONE |
| Type111 array position matters | NO for Type111 itself; order among other supported entries remains separate |
| Delegation | ORIGINAL request |
| Type111 request fields | `type=111`; `streamConnectionID` required in MHI2, Honda Type111 unknown; other fields opaque |
| Type110 response | `{type:110,dataPort}` |
| Type111 response | MHI2 actual pattern: cloned descriptor plus `dataPort`, `streamID=111`; Honda UNKNOWN |
| Mutable response streams | YES |
| Post-Setup append | structurally YES |
| SessionStart | Honda Type110 Setup initializes listener/security and may call _ScreenStart; MHI2 binds Type111 state after stock SessionStart; Honda Type111 requirement unknown |
| Type111 teardown | project-owned close listener/socket/crypto/parser/config state on explicit stream or whole-session teardown |
| Partial stream teardown | Honda supports recognized 100/101/110; Type111 receives no stock cleanup; project must own it |
| New generation | new Setup/connection ID resets project-owned listener, CTR, parser and config generation |
| First Type111 request gate | exact phone trigger/response acceptance unknown |
| Two hooks sufficient for TCP proof | UNKNOWN; phone-side Type111 trigger and response identity is the remaining gate |
| Type110 screen KDF offline model | READY with synthetic vectors |
| Type111 KDF reuse on Honda | UNKNOWN |
| Offline Setup augmentor/session model | READY as explicit prior-art model |
| Complete offline Type111 composition model | READY at transaction/crypto/parser/lifecycle abstraction level; no listener socket |
| Safe offline interposer implementation next | YES |
| Live Type111 TCP test | NO |

**Biggest Setup blocker:** Honda/iPhone Type111 response acceptance and the exact request trigger remain unobserved.
**Biggest security blocker:** Honda does not call the recovered screen KDF for Type111, so Type111 key/CTR compatibility is not target-proven.

## Sources

- Honda evidence: local `jmcs` static disassembly/DWARF, SHA-256 above.
- MHI2 source, pinned commit: [libaltscreen111_gen2.c](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/src/native/altscreen111-gen2/libaltscreen111_gen2.c).
- MHI2 hook/porting checklist: [MU1440_GEN2_HOOK_MAP.md](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/MU1440_GEN2_HOOK_MAP.md).

## Verification

`python3 -m unittest discover -s tests/transport -v`: 29 passed. `python3 -m unittest discover -s tests/negotiation -v`: 18 passed. `git diff --check`: pass.
