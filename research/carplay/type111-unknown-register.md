# Type 111 unknown register

All rows are unknown for Honda. Offline tests validate candidate handling but cannot resolve wire behavior.

| Unknown | Current evidence | Impact | Offline test | Live evidence | Next reduction |
|---|---|---|---|---|---|
| Exact Type111 response fields | Honda skips; MHI2 is prior art | Phone may reject/ignore | Candidate profiles, strict unknown rejection | Yes | Trace response after safe entry exists |
| Need for second /info descriptor | Array exists; stock emits one | Phone may never request stream | Candidate state only | Yes | Fingerprint exact capability generation |
| Display UUID ↔ stream mapping | No Honda join | Wrong display binding | Enforce no default mapping | Yes | Correlate advertised/requested fields |
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

No real keys or captured proprietary payloads are used.

Step 42D fixtures keep all fields that affect display correlation, response shape, stream crypto, and codec readiness explicitly candidate/synthetic. An injected missing-field case fails closed; no implicit Honda default is added.

Step 42E's replay preserves these unknowns in both modes: strict mode skips the candidate; hypothetical mode marks its cloned response profile as MHI2-derived, values as synthetic, display-to-stream correlation as unknown, and key/IV behavior as unknown without running Type111 crypto. The synthetic second descriptor is not linked to the request's synthetic correlation value as a Honda rule. A deterministic pattern frame after successful synthetic parsing proves only model composition.
