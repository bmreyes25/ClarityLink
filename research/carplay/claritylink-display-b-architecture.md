# ClarityLink Display B architecture after Step 34

## Transport plane

```text
Type-111 SETUP request
  -> preserve peer descriptor and unknown fields
  -> read per-stream streamConnectionID
  -> use authenticated stock session security context
  -> stock per-screen key derivation (Honda compatibility unproven)
  -> own Type-111 listener and response data port
  -> accept on that dedicated listener
  -> Honda-compatible decrypt/framing -> H.264
```

Honda proves this pattern for Type 110 through an ephemeral listener and a `{type:110,dataPort}` response. MHI2 source supplies evidence for a target-specific Type-111 implementation using stock session crypto material and a cloned request descriptor. Neither proves Honda Type 111.

## Presentation plane

```text
/info display descriptor and UUID
  -> capability/display negotiation
  -> suggestUI candidate list
  -> showUI / stopUI / ViewArea state
  -> cluster UI ownership
```

Honda's numeric display UUID has no demonstrated mapping to `streamConnectionID`. Keep the UUID in the advertised display/capability model; do not require it to identify the transport socket. The phone's ability to request Type 111 may still depend on presentation-plane advertisement/capabilities.

## Minimal Type-111-compatible setup model (hypothesis)

1. Preserve the original SETUP root request and every unrecognized field.
2. Clone its stream array into stock and ClarityLink subsets, retaining every non-111 stream in the stock subset.
3. Let stock process normal 100/101/110 streams unchanged.
4. For Type 111, use the request's actual connection ID and established stock session security context with the target-compatible stock derivation mechanism.
5. Bind a separate listener and append a response entry derived by cloning the requested descriptor, changing only fields proven necessary for the response.
6. Keep transport generation, socket, crypto context, and cleanup state owned by one Type-111 session record.
7. Defer UI ownership/rendering commands while proving only connection plus valid decrypted screen header/VideoConfig.

Unknowns remain explicit: exact Honda Type-111 fields, whether request uses `type` or another key, response identity field (`type` versus `streamID`), phone correlation behavior, derivation parity, listener ownership/teardown, frame envelope and VideoConfig encryption boundary, and whether Honda/iOS version requires feature tokens.

## Readiness

| Component | Status |
|---|---|
| Server-info augmentor | READY as offline boundary only; descriptor values/capability semantics need evidence |
| Type-111 setup model | READY as a labeled hypothesis, not wire contract or implementation |
| Crypto model | PARTIAL; derivation dependencies clear, Honda Type-111 compatibility unknown |
| Screen framer | NOT READY; Honda TCP/record grammar not recovered |
| Offline implementation | NO; no handler/code should be implemented from assumed schema |
| Live transport test | NO |

## First success gate

Keep primary CarPlay stock; observe phone Type-111; return a compatible response and listener; accept phone TCP; confirm a valid secondary header or VideoConfig after decryption. This would prove transport. `suggestUI`, `showUI`, rendering, and ViewArea are later presentation work. Transport-before-UI is demonstrated in MHI2's architecture/lifecycle evidence, but remains unproven for Honda.
