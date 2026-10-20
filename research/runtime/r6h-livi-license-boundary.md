# R6H LIVI license and dependency boundary

- Upstream: `https://github.com/f-io/LIVI`, pinned `dcb78854c59ba621f4d327910dc275da386496b4`, package 9.2.0, GPL-3.0-or-later; no submodules.
- Isolated reproducible source patch: `third_party/patches/livi/0001-control-delegate-dispatch-and-bounds.patch`, SHA-256 `3756b472f4ee07f67dbd4a986055c97df7a2a970a36e6ce8768ee07d57b917d8`.
- Patch files: `CpSession.ts`, `cpStack.ts`, `types.ts`, `controlDelegate.ts`, `liviUnixControlDelegate.ts`, RTSP parser, and focused tests. It contains original integration code, not a vendored LIVI source tree or binary.
- ClarityLink/Python communicates using documented local IPC framing and exchanges structured request/response plists; no implementation code is copied into ClarityLink.
- Current source dependencies were installed from the pinned lockfile with lifecycle scripts disabled. TypeScript typecheck and 20 focused tests passed. Native LIVI crypto build/full `CpStack` tests were unavailable because Cargo is absent.
- Distribution of a combined LIVI+ClarityLink product may create GPL obligations; this record is technical/license fact only and does not decide legal compatibility. Obtain appropriate legal review before combined distribution.
