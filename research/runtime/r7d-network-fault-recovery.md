# R7D network fault recovery

The R7D network mode reruns the production AndroidSocketAdapter fault matrix, then performs 25 fresh dual-stream loopback reconnects with fragmented synthetic H.264 frames. It records explicit Type111-local versus Type110-session-global handling, resource zero after every session, and idle checkpoints. R7C already proved timeout, refusal, peer close, malformed/truncated frames, zero/oversized declaration, wrong stream/generation, and active read/write shutdown through the Android adapter.

## Result

`R7D_NETWORK_RECOVERY=PASS`: full production AndroidSocketAdapter matrix passed, followed by 25/25 dual-stream reconnects. Scope assertions distinguish Type111-local faults from Type110 session-global refusal. All session owner counts and race-controller state returned to baseline after each reconnect.

Evidence: [`/tmp/claritylink-r7d-network-final-runtime.log`](/tmp/claritylink-r7d-network-final-runtime.log) and [`/tmp/claritylink-r7d-network-final.log`](/tmp/claritylink-r7d-network-final.log).
