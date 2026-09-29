# Honda Type-111 interception boundary — Step 34

Honda's `AirPlayReceiverSessionSetup` (`0x2854e0`) parses the streams array as a per-entry loop. It dispatches 100/101 to audio, 110 to screen setup, and sends 111 to the invalid-type branch beginning at `0x2861f6`. Type 110 uses the current stream dictionary, the screen session at receiver offset `+0x14`, a `uint32_t` session ID from receiver context, and the shared response-stream array/builder. It also reads `streamConnectionID` as uint64 in the inlined `_ScreenSetup` path.

**Conceptual intercept:** at per-entry type dispatch, before 111 reaches the invalid branch. This affords access to the receiver/session context, current stream dictionary, type value, and shared Setup response builder/array in the static flow. Exact stable C ABI, register/stack argument contract, ownership, cleanup requirements, and reentrancy are not validated as a hook ABI.

| ABI component | Evidence-bounded status |
|---|---|
| receiver/session pointer | Available to Setup (`r0`) |
| request dictionary | Available to Setup (`r1`); current element held during loop |
| response output dictionary | Setup output pointer (`r2`); response streams list is used by loop |
| error/status | OSStatus flow exists; exact externally visible Type-111 status unknown |
| per-entry continuation/delegation | Loop exists, but partial success/rollback semantics for mixed entries are unknown |
| Type-111 crypto/listener parity | Unknown; stock Type-110 uses `streamConnectionID` in AES key/IV derivation |

No implementation is ready. A wrapper that lets stock process 100/101/110 and handles 111 is structurally plausible, but the response/error object state and failure cleanup need exact recovery before claiming safe partial delegation.

## Delegation analysis

Recommended eventual structure: a wrapper around the per-entry dispatcher / Setup boundary, splitting only Type-111 entries away from the stock call while preserving the original root dictionary and all non-111 stream dictionaries. Call stock with the cloned request containing normal 100/101/110 entries, then append the separately built Type-111 response to the stock result only after stock succeeds. The incoming Type-111 descriptor itself should be cloned before changing response-only fields. This is the strongest design candidate because it isolates Honda's known invalid branch while retaining normal stream handling and unknown fields.

| Option | Assessment |
|---|---|
| A. clone request and remove Type 111 before stock | Strong candidate for isolated Type-111; whether stock tolerates empty streams and partial setup rollback remains unknown |
| B. split streams into stock / ClarityLink subsets | Conceptually safe if root and descriptors are preserved; same partial-success/ordering uncertainty |
| C. call stock with original, then repair Type-111 failure | Unsafe: stock invalid-type path may fail/cleanup before any response is available |
| D. wrapper around per-entry dispatcher | Best conceptual seam if hook ABI is validated; can preserve exact stock branches but carries highest implementation/ABI risk |

For a first offline model, combine A/B at the outer Setup wrapper. Avoid C. A per-entry hook (D) is an alternative only after proving its ABI, cleanup, and mixed-entry semantics. `PRIMARY_STREAMS_PRESERVED=YES` as a design property when the original non-111 entries are cloned verbatim and stock is called with them; actual Honda mixed-stream success remains UNKNOWN. MHI2 uses stock-first with its original request for its target and a version-specific patched stock path; do not copy that strategy onto Honda, where 111 takes an invalid branch.

No hook or handler is implemented. Live interception safety and Honda Type-111 response fields remain unknown.
