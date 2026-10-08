# R7C1 restoration verification

The offline restoration verifier requires the receiver closed, zero session/listener/security/decoder counts, zero retained host frame bytes, Display0 and Display1 clear, both surface cores invalidated, synthetic JNI handle table empty, and every modeled process/adapter lease released. A normal dual-stream run, the Type111 display-failure run, and each of the 100 normal integrated cycles satisfy this oracle. The Type110 failure case closes both streams and rejects later Type111 input.

This is proof of cleanup for the model and host-simulated owners. It does not verify Android process termination, actual framework listeners/Surface release, factory `jmcs` state, Honda display contents, warning layers, stock audio/controls, or factory-state restoration. `HONDA_STOCK_RESTORATION` remains `EVIDENCE_REQUIRED`.
