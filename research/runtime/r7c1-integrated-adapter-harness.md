# R7C1 integrated adapter harness

Command: `tools/test_r7c1_integrated.sh`.

The harness exercises the actual `ReceiverGeneration`, actual R7B FFmpeg H.264 decode and RGBA conversion, actual `SurfaceSinkCore`, and its host fake Android window. Type110 and Type111 fixtures decode independently to generation/stream-specific outputs with distinct pixels. It also tracks modeled process, JNI table entries, generation, streams/listeners, decoders, security providers, transports, surfaces/native-window tokens, audio, input, USB, iAP2, auth, socket, and process resources. Normal and injected Type111-display-failure flows verify teardown to zero. The malformed Type111 fixture verifies secondary teardown and Type110 continuation. A primary-surface failure closes the whole receiver session.

The 100-cycle path includes two surfaces, both H.264 decoders, both streams, test-authority mode, synthetic setup, modeled adapter ownership, disconnect/close, surface clear/release, registry erase, and post-cycle zero counters. Each cycle is checked individually; generation IDs advance each time. Production authentication and security fail-closed checks run separately. Focused runs also invalidate Display1 after a successful Type111 frame, reject subsequent secondary frames, release Type111 resources, and prove Type110 continues.

## Results and limits

- Environment: macOS host C++17; FFmpeg 9.0.2 host libraries; `HOST_SIMULATED_ANDROID_RUNTIME`.
- Result: 100/100 cycles clean; actual H.264 decode and two SurfaceSinkCore outputs passed; Type111 display/media failure preserved Type110; primary display failure stopped the full model session.
- Normal, ASan/UBSan, and TSan harness executions passed.
- The resource oracle is explicit host RAII accounting plus `ReceiverGeneration::resources()` and fake-buffer clearing. It is not instrumentation of ART, ANativeWindow, Android AudioTrack, USB host, Honda services, or Android process memory.
- Socket adapter still uses its separate actual loopback POSIX test. The integrated socket/audio/input/USB/iAP2/auth entries are offline lifecycle contracts/counters; this harness does not exercise the Java adapter implementations end-to-end.
- No Android JVM, emulator, or device execution occurred. This is meaningful offline receiver/surface-core integration, not a full Android/JNI all-adapter integration pass.

## ECC review

The stream generation is passed into each Stream and used on clear. Secondary frame/decode errors release Type111 resources and recompute session state. Type110 decode/output failure releases both streams and sets the session `Closed`; primary functionality is session-global. Resource counters are checked after each run, not only at the end. The lifetime race in SurfaceSinkCore is controlled with a condition variable, not a timing sleep. Remaining limitations are called out above and in the R7D entry gate.
