# Digital twin audio state model

**Classification: SYNTHETIC_INVARIANT.** The fields below assert isolation behavior only. They do not describe a recovered Honda audio focus API or exact CarPlay audio routing implementation.

State:

- center CarPlay audio: active/inactive
- navigation voice route: active/inactive
- audio focus owner: synthetic token or none

Invariants:

1. Type111 negotiation, listener, crypto, parser, decoder, and renderer failures do not modify these audio fields.
2. Type111 disconnect does not modify these audio fields.
3. Type110 stream-only disconnect has no modeled audio side effect; whether Honda ties these lifecycles together is unknown.
4. Full CarPlay session disconnect clears the audio fields.
5. Tests use symbolic state only; no audio payload or private focus data is stored.

The Step 42D twin encodes these fields in a separate AudioState object. Type111 failure tests compare it byte-for-byte (stable JSON form) before and after each injected failure. Full session disconnect clears it. Type110-only disconnect behavior is explicitly a twin policy and remains unknown for every Honda lifecycle edge.
