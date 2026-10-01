# Type 111 unknown register

## Step 43N external evidence update (2026-10-01)

Pinned DiPlay (`f2d06951b4e8114dbb62f551c12a32a845a3042f`) and PlayPort (`9a0882dd0ffe48e467b59d58b12d81391df55ade`) now provide **EXTERNAL_PRIOR_ART** for a separate display/stream 111, `altScreen` and `viewAreas` negotiation, distinct Type111 `dataPort`, and UUID-scoped alternate-display controls. DiPlay's pinned documentation reports iOS 27 physical cluster-map validation (**EXTERNAL_PHYSICAL_VALIDATION**). None of these facts establish Honda behavior. The unknown register remains Honda-scoped: Honda Type111 descriptor fields, `initialURL`, feature negotiation, request acceptance, UUID↔stream identity, crypto, and UI control all remain `HONDA_UNKNOWN`. See [DiPlay differential](diplay-type111-differential.md), [PlayPort differential](playport-type111-differential.md), and [Honda/security comparison](honda-vs-modern-type111-security.md).

Step 43H ownership/lifecycle update (2026-09-30): Setup dictionary and `streams` array retaining callbacks, Type110 entry ownership, and post-send project session cleanup are still unknown. The CF response graph is no longer needed after successful synchronous serialization; a future Type111 listener would need an independently proven connection/session lifecycle cleanup edge. This does not establish Honda Type111 behavior or readiness. See [Step 43H](../../step-reports/43h-cf-callback-fingerprint.md).

Step 43G partially resolves callback wrapper behavior but does not tie all callbacks to Setup's constructor arguments or complete the Type110 retain/release ledger. It also confirms that later HTTP queue/write failures occur after response-graph release, while project cleanup linkage remains unknown. Honda Type111 wire/schema/security/display unknowns and caller-side race safety remain open; see [CF callback ownership](honda-cf-callback-ownership.md) and [caller liveness](honda-post-setup-caller-liveness.md). No implementation/live gate changes.

All Type111 wire/schema rows remain unknown for Honda. Step 43B narrows some static descriptor questions but does not establish Type111 behavior. Offline tests validate candidate handling but cannot resolve wire behavior.

| Unknown | Current evidence | Impact | Offline test | Live evidence | Next reduction |
|---|---|---|---|---|---|
| Exact Type111 response fields | Honda skips; MHI2 is prior art | Phone may reject/ignore | Candidate profiles, strict unknown rejection | Yes | Trace response after safe entry exists |
| Need for second /info descriptor | Array exists; stock emits one | Phone may never request stream | Candidate state only | Yes | Fingerprint exact capability generation |
| Display UUID ↔ stream mapping / UUID semantic role | `/info` inserts numeric Screen `uuid`; Setup independently reads stream `type`, Type-110 `streamConnectionID`, then returns `type`/listener `dataPort`. No direct join was found in those traced paths; semantic UUID role remains unknown for Honda. | Wrong display binding or mistaken coupling of presentation, input, transport, and crypto identities | Enforce no default mapping | Yes for phone-side selection; obtain broader Honda source for any internal join | Complete stock-first seam review, then only a reviewed observation milestone if needed |
| Type111 streamConnectionID source | Type110-only Honda read | Crypto binding unavailable | Synthetic validation | Yes | Trace actual request and receiver |
| dataPort expectations | Type110 ephemeral; MHI2 separate | Connection fails | Fake listener lifecycle | Yes | Observe secondary transaction |
| Key/IV derivation and master reuse | Type110 KDF confirmed; Type111 absent | Decryption/authentication fails | Candidate isolation only | Yes | Trace legitimate Type111 security inputs |
| Separate timing fields/state | No Honda path | Synchronization failure | Yes | Yes | Compare Setup/header behavior |
| Feature advertisement prerequisite/generation | Old /info vs newer capability models | Phone may not ask | Branch model | Yes | Controlled capability trace |
| Receiver capability sufficient | R15 support unproven | Negotiation may fail | Partial structural model | Yes | Fingerprint and controlled phone negotiation |
| Type111 request parser needed | Honda skips default path | No response today | Parser contract | Yes | Define after request shape known |
| Connection initiator/start order | Type110 listener suggests phone connects; Type111 absent | Wrong listener timing | Event order model | Yes | Observe after response |
| Teardown/reconnect semantics | Honda parent lifecycle only | Stale state/cross-session crypto | Generation tests | Yes | Trace disconnect/reconnect |
| ScreenStream/H.264 reuse | Honda Type110 only; MHI2 own path | Parser incompatibility | Synthetic variants | Yes | Obtain legitimate secondary stream evidence |
| Parallel Honda display descriptor source | `ScreenCopyMain` selects registry index 0; descriptor builder calls it once; no alternate source recovered in audited path | Existing `/info` producer may have no path to a second descriptor | Structural collection tests only | Yes, for actual advertised behavior | Expand key/function xrefs beyond recovered builder; later observe controlled Honda transaction |
| `forceKeyFrame` semantics / Type111 relation | DWARF names `AirPlayReceiverSessionForceKeyFrame` and gives parameter names, but its low-PC-zero range is not a usable body; saved symbol/disassembly inputs have no function body or resolved key xrefs. The recovered `ProcessFrames` switch sends opcode 3 to its unrecognized path. | Whether this is screen refresh, decoder recovery, UI/control, or phone-facing remains unknown; no Type111 link was recovered | Keep all candidate semantics explicit; do not model opcode 3 as keyframe | Yes, for runtime semantics | Obtain complete function-level jmcs debug/disassembly inputs; next static priority is Setup `type` / `streamConnectionID` against display UUID |

No real keys or captured proprietary payloads are used.

Step 42D fixtures keep all fields that affect display correlation, response shape, stream crypto, and codec readiness explicitly candidate/synthetic. An injected missing-field case fails closed; no implicit Honda default is added.

Step 42E's replay preserves these unknowns in both modes: strict mode skips the candidate; hypothetical mode marks its cloned response profile as MHI2-derived, values as synthetic, display-to-stream correlation as unknown, and key/IV behavior as unknown without running Type111 crypto. The synthetic second descriptor is not linked to the request's synthetic correlation value as a Honda rule. A deterministic pattern frame after successful synthetic parsing proves only model composition.

Step 43C leaves `forceKeyFrame` as `HONDA_UNKNOWN`. The separate ForceKeyFrame body/callers are not recoverable from the preserved jmcs artifacts; string literals do not establish ownership or semantics. In the recovered ScreenStream dispatch only, opcode 3 is unrecognized. No Type111, control-plane, or decoder-recovery meaning is established. See [Step 43C](../../step-reports/43c-forcekeyframe-semantics.md) and [the Honda analysis](honda-forcekeyframe-semantics.md).

Step 43D confirms that Honda Setup stream `type`, Type-110 `streamConnectionID`, and the listener's `dataPort` form a recovered stream-control path distinct from the `/info` Screen `uuid` insertion path. The direct UUID-to-stream binding was not found in the traced code; UUID role stays `HONDA_UNKNOWN`. See [Step 43D](../../step-reports/43d-setup-stream-identity-correlation.md), [Honda Setup identity](honda-setup-stream-identity.md), and the [pinned external prior-art note](setup-stream-identity-prior-art.md).

Step 42F exposes response schema, display/stream correlation, Type111 security, ExternalDisplay frame handoff, jmcs load seam, and crop/mask as visible `UNKNOWN` items in the visual demo. The hypothetical view does not collapse them when its synthetic frame appears.

Step 42J proves that generated synthetic H.264 can be adapted into the existing parser's modeled opcode-1 config and opcode-0 AVCC frame path and decoded on the host. It does not change any Honda unknown: no Honda Type111 response, stream correlation, security fields, encrypted payload, phone request, or actual ExternalDisplay handoff was observed. The ScreenStream fixture uses `PLAINTEXT_SYNTHETIC` and must not be treated as Honda-confirmed.
# Step 42G update — host decoder

Host H.264 decoding is implemented only as an optional FFmpeg adapter. The host in this step lacks FFmpeg, and the replay fixture is not valid H.264. Actual host decoding is therefore still UNKNOWN/NOT RUN; the digital-twin image remains a synthetic pattern. Honda decoder compatibility and Type111 video syntax remain UNKNOWN.
# Step 43G callback/cleanup status (2026-09-30)

The stock-first response seam remains a static candidate only. Named CFL array/dictionary callback tables are recorded, with retain/release/equality wrappers delegating to CFL operations, but the Setup response dictionary's exact callback arguments and the Type110 entry's full ownership ledger are unresolved. Do not treat table presence as proof of constructor use. Serializer failure releases the Setup response through caller cleanup; later HTTP queue/write failures use independent connection state. The callback-to-project/session cleanup edge is still unknown. Classification remains `NEEDS_MORE_STATIC_PROOF`; no Type111 implementation or live gate is authorized by this evidence. Details: [Honda CF callback ownership audit](honda-cf-callback-ownership.md).

## Step 43L.1 register boundary update

In `_connectionHandleMessage`, Setup at `0x28af72` receives `r0=session`, `r1=request`, `r2=&responseOut`. At the best structural candidate after stock metadata (`0x28afb2`), durable values are reloaded from `[r10+0xf4]`, `[sp+0x1c]`, `[sp+0x54]`, and `[sp+0x50]`; `r4` connection and `r6` HTTP message are callee-saved. Caller-saved `r0-r3/r12` are not durable. This caller ABI is not a Honda Type111 request ABI. Honda Setup still skips unsupported Type111, and no descriptor/security/dataPort semantics are established. Generic position-independent `streams[*].type == 111` inspection is a `SYNTHETIC_TEST_VALUE` project rule and must remain read-only. See [43L.1 callout/cleanup audit](../../step-reports/43l1-callout-safety-cleanup-reachability.md).

## Step 43L.2 lifecycle update

Honda has an interface event named `MC_DEV_CARPLAY_SESSION_DESTROYED`, but it is not Type111/session cleanup evidence: it is emitted through a single global callback slot, its setter replaces the whole callback record, and its callback arguments omit the AirPlay session identity. Project cleanup remains generation-owned with synthetic bounded lease/reap behavior. All Type111 schema, crypto, negotiation, identity, and live behavior rows remain `HONDA_UNKNOWN`; this milestone changes none of them. See [43L.2 finalizer audit](../../step-reports/43l2-session-finalizer-extension-audit.md).
