# R7C1 resource accounting

The host harness tracks JNI table handles, generation owners, stream adapters, SurfaceSinkCore adapters, simulated native-window tokens, decoder/security/transport/listener state, audio/input/USB/iAP2/auth/socket adapters, and process lifecycle owners. The receiver additionally reports sessions, listeners, security contexts, decoders, retained frames, and display ownership.

The integrated normal path snapshots two listeners, two security providers, and two decoder instances while active. After disconnect it checks receiver counters, surface clear bytes, invalidation, registry emptiness, and every host ownership counter equals zero. The 100-cycle loop calls that oracle after each cycle. Injected Type111 display and decode failures also run teardown and zero checks.

Method limitations: decoder/provider/transport counters in the adapter oracle are explicit leases that mirror expected R7C ownership; they are not exported internal FFmpeg allocation counters. No platform ANativeWindow ref counter, JNI VM global-ref counter, Android heap/RSS trace, or Honda resource count is available. This report makes no memory-growth claim beyond bounded test buffers and zero tracked project-owned host tokens.
