# R6A API17 / ARMv7 port plan

No target execution or build occurred. First native slice: bounded plist-adjacent Setup structs, stream ID uniqueness, generation-owned listeners and parser primitives, built as a host library with sanitizer tests and shared fixtures. Next: Android NDK API17 ARMv7 cross-compile with Bionic-compatible sockets/threads and no Python/FFmpeg process dependency. Then verify `ANativeWindow`/Surface and available Stagefright codec ABI against preserved artifacts; preserve a hardware decoder fallback decision until measured. Finally implement Honda transport/auth/audio/control/display adapters only where static evidence identifies the interface. Do not link to guessed private symbols or deploy. [R5Z audit](r6a-r5z-code-promotion-audit.md) and [language ADR](../adr/r6-receiver-language-and-portability.md) track the split.

The canonical shared semantic fixture is [`tests/fixtures/r6/protocol-vectors.json`](../../tests/fixtures/r6/protocol-vectors.json). It is synthetic and sanitized, with no Honda or phone capture.
# R6C factory substrate adapter note

The preserved Honda build compiles USB/iAP2/authentication and AirPlay receiver into `jmcs`. No external ABI for an authenticated session or I²C auth provider has been established. The target C/C++ port therefore retains an opaque, generation-scoped factory-session interface returning `EVIDENCE_REQUIRED` until ownership, threading, permissions and close behavior are documented. See [R6C adapter ABI](r6c-honda-auth-adapter-abi.md). No direct `/dev/i2c-2` access or deployment path is part of the port.
