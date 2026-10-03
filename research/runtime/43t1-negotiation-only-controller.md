# 43T1 negotiation-only controller — offline model

**Decision: `NEGOTIATION_CONTROLLER_MODEL_READY` for synthetic event order.** Source: `NegotiationController` in `src/claritylink-honda/prep2_runtime.py`.

The sequencer requires baseline → verified attachment → Setup wait → observed Type111 request → ready listener → prepared response extension → one stock serializer call → local serializer success → separate phone connection evidence → bounded first bytes → generation retirement → detach → restoration evidence → complete. It rejects skipped or repeated states. Local serializer success does not imply phone connection.

Bounds in this clean-room controller are one connection, a two-second accept window, a 0.25-second first-byte window, 256 first bytes, and a five-second synthetic total event-time lease. The loopback integration sets a host socket timeout for the prefix read. These are model limits only, not Honda timeout or protocol values. No reconnect or repeated Setup loop exists. The Type110 ownership/close/reset flags, audio, and center-display state are invariants checked at each transition. The controller has no decryptor, decoder, renderer, cluster output, or automatic next experiment.

The composed host test uses a test-only loopback listener and a synthetic CF graph. It calls a serializer stand-in once, observes a host connection, captures one 128-byte synthetic prefix, closes the generation, retires bridge objects, detaches the RAM simulation, and independently checks stock facts. This is not Honda Type111 acceptance/reachability evidence. Failures/unknown bytes stop the experiment; the security oracle never chooses AES or ChaCha.
