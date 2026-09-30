# Stock Type 110 invariants

Step 42C contract for offline models and future integration. Honda-confirmed means static behavior recovered from archived Honda artifacts, not live-interoperability proof.

| Invariant | Honda confirmed | Must preserve | Testable offline |
|---|---:|---:|---:|
| Stock Setup handles its existing stream list and supported entries | Yes | Yes | Yes, model semantics |
| Successful Type110 response retains type=110 and Honda dataPort | Yes | Yes, unchanged | Yes |
| Nonzero Type110 streamConnectionID feeds screen crypto | Yes | Yes | Yes with synthetic values |
| Recovered SHA-512 KDF uses session master plus decimal-ID salts; type is not an input | Yes | Yes | Yes |
| Type110 has its own listener, parser, CTR and decode/render path for center CarPlay | Recovered static path | Yes | Partial; twin cannot execute Honda path |
| Honda audio and disconnect/reconnect remain Honda-owned | Yes generally; some edges incomplete | Yes | Partial, synthetic lifecycle |
| Type111 failure cannot corrupt Type110 state | ClarityLink rule, not Honda Type111 behavior | Yes | Yes |

## Hard rules

1. Stock Setup first. On its failure, allocate and advertise no Type111 state.
2. Do not rewrite, reorder, delete, or replace stock response entries. Preserve opaque stock fields.
3. Type111 listener, crypto, parser, decoder, and lifecycle state are independent and generation-scoped.
4. Candidate preparation/merge failure closes project-owned resources and returns the unchanged stock response.
5. Type111-only disconnect cannot reset Type110. Parent-session teardown closes Type111 with its parent. If the parent/Type110 session fails after Type111 starts, proposed policy is to close the child without mutating Honda internals.
6. Synthetic equality does not prove exact wire-byte identity or phone acceptance.

## Existing tests

The negotiation suite covers stock-first order, stock failure short-circuit, Type110/audio entry preservation, unknown fields, candidate rollback, and atomic malformed merge. The display/session fixture checks primary preservation and labels its tokens synthetic. These guard the model, not Honda Type111 support.

Step 42D's failure twin additionally compares an immutable Type110/session/audio snapshot across injected listener, crypto, parser/config, frame, renderer, duplicate-request and secondary-teardown failures. Parent stream loss closes the modeled secondary; full session loss clears audio. All audio fields are synthetic invariant-only.
