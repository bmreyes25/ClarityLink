# R6C clean-room target adapter ABI

Target constraints: C/C++, ARMv7, Android API 17, Bionic. The only implementation-ready contract is **our side** of the boundary: an opaque generation-scoped context, request/response transport, and explicit close. The Honda source ABI is not established as an external callable API, so no C symbol binding, vtable layout, ioctl, Binder transaction, or socket framing is declared.

Conceptual types (not proprietary declarations):

```text
FactorySessionRef: opaque, non-serializable, generation-owned
FactoryAuthProvider.open() -> FactorySessionRef | EVIDENCE_REQUIRED
FactoryControl.read(ref, timeout) -> structured request | EVIDENCE_REQUIRED
FactoryControl.write(ref, response) -> status | EVIDENCE_REQUIRED
FactoryControl.close(ref) -> invalidate once
```

The provider must never expose chip private material; certificate and signature operations, if ever needed, stay behind the factory owner. A future ABI review must establish exact calling convention, ownership, thread affinity, permissions, session generation, request encoding, failure and close behavior before any native implementation. No deployment tooling is present.
