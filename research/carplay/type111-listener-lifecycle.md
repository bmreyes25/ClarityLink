# Type 111 listener lifecycle contract

Candidate only; Honda Type111 listener is not observed or implemented.

IDLE -> PREPARING -> LISTENING -> ADVERTISED -> CONNECTED -> STREAMING -> CLOSED.

1. Prepare only after stock Setup succeeds and a candidate Type111 request exists. Keep generation, ID, crypto, parser, codec, and listener isolated.
2. Bind a project-owned listener first; publish dataPort only after successful bind/listen. Type111 port semantics remain unknown.
3. Append to a copy of stock response. If serialization/send fails, close candidate listener.
4. Current 128-byte header and opcode 1 config / opcode 0 video interpretations describe Honda Type110 evidence only. Type111 reuse is hypothesis. Bound lengths and reject malformed messages.
5. Type110-informed model also classifies control opcodes 2/4/5 and unknown messages; Type111 meanings remain unknown.
6. Disconnect clears listener, parser, config and CTR for this generation. Reconnect creates a new generation; never reuse partial bytes/counters.
7. Type111-only failure clears only Type111 and renderer state. Stock Type110/audio state is unchanged.
8. Parent Setup/session end closes Type111 with its parent; do not mutate Honda-owned Type110 internals.
9. Malformed frames terminate/quarantine only the candidate generation.

Existing tests cover lifecycle generations, invalid IDs/ports/transitions, stock-first failure short-circuit, candidate rollback and ScreenStream parser bounds/reset. These test synthetic behavior only; no real Type111 socket exists.

Step 42D failure-injection tests cover candidate descriptor/ID/response failures; allocation/bind/listen/accept; partial disconnect; derivation/IV/CTR failure; header/body/opcode/config/H.264 errors; renderer/host failures; duplicate requests; secondary-only disconnect; parent Type110 disconnect; and whole-session teardown/reconnect. Each secondary failure is checked against a snapshot of Type110 and synthetic audio state.
