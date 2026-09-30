# Runtime preload compatibility probe (synthetic; not run on Honda)

The probe is a standalone Android API 17 / ARMv7 compatibility executable and preload library. It does not load or modify jmcs and contains no Honda/CarPlay APIs, network, CAN, display access, or persistent-write behavior.

## Probe source and build

- `src/claritylink-probes/preload/probe_exec.c`: writes `CLARITYLINK_PROBE_MAIN_RAN` to stdout and exits 42.
- `src/claritylink-probes/preload/probe_preload.c`: constructor writes `CLARITYLINK_PROBE_CONSTRUCTOR_RAN` to stderr and returns normally.
- `build_probe.sh` accepts a local Android NDK r23c root and an absolute output directory outside the repository. It targets ARMv7/API 17 and does not execute the outputs.
- `tests/preload-probe/test_probe_artifacts.py` checks ELF class/architecture/type, interpreter, libc dependency, SONAME, and markers. It does not emulate or execute ARM code.

The local NDK r23c image was mounted read-only from `/Users/bmreyes24/Downloads/clarity-ndk/android-ndk-r23c-darwin.dmg`. Toolchain was Android clang 12.0.9, target `armv7a-linux-androideabi17`. Generated artifacts were built under `/tmp`, validated, hashed, and deleted; only source/build/test files are committed.

| Artifact | SHA-256 (metadata only; generated binary removed) |
|---|---|
| `claritylink_preload_probe_exec` | `c7666bfabdbe9b917a51316105f2cbc5a824c12a6eb03fffa7c04760875de4f0` |
| `libclaritylink_preload_probe.so` | `abbe2a35886673019007f205f44536cc7f26b1c35aa69135008bf99c8aa58983` |

Three artifact tests passed. The executable is ELF32 ARM EABI5 PIE, dynamically linked with interpreter `/system/bin/linker`, and depends on `libc.so`. The library is ELF32 ARM EABI5 `ET_DYN`, SONAME `libclaritylink_preload_probe.so`, and depends on `libc.so`.

## Future parked probe plan (not executed)

In a separately scoped, authorized parked-car milestone, stage only the probe executable/library under `/data/local/tmp`, run the executable normally and with its absolute-path preload, then run missing/invalid preload cases against the probe executable only and remove both files. Do not point any case at jmcs. Keep failure cases isolated to this standalone process.

This tests the head-unit linker and the shell process's ability to execute/map from that path. It does **not** prove the jmcs service's SELinux domain, secure-exec state, root environment, or mmap permissions. A successful probe is a reason to reassess the jmcs-specific gate, not authorization to change its init stanza. A failed preload only demonstrates behavior for the test process.

Status: source/build validated; local ARM execution unavailable; no vehicle, ADB, or staging performed. The future parked probe design is ready for a separate milestone. jmcs no-op load remains **NOT READY**.
