# R6G LIVI public source baseline

Retrieved and reviewed 2026-10-05 from [f-io/LIVI](https://github.com/f-io/LIVI), exact commit [`dcb78854c59ba621f4d327910dc275da386496b4`](https://github.com/f-io/LIVI/tree/dcb78854c59ba621f4d327910dc275da386496b4). A shallow public-source checkout at that SHA was used for read-only inspection; no upstream source was copied into this repository.

## Provenance and license

- Repository: `https://github.com/f-io/LIVI.git`; branch observed: `main`; checkout SHA above.
- `package.json`: `9.2.0`, `GPL-3.0-or-later`; Electron/TypeScript application. No submodules are declared.
- Workspace includes `livi-crypto`, `livi-gst-video`, `livi-host-proto` and `livi-helperd`; Rust native components use Cargo workspaces. The helper/provisioner includes USB, network, Bluetooth/iAP2, provisioning and MFi coprocessor integration. The app also packages GStreamer/native media components.
- Project build scripts include macOS arm64/x64 targets. The link documentation describes LIVI Link on macOS; Linux-only BlueZ/vhci details do not establish a macOS iAP2 stack API.
- Dependencies are managed with pnpm (`pnpm@12.8.1`) and Cargo. This review did not install or execute LIVI, provision hardware, or test iPhone behavior.

## R6G relevance

`CpManager` owns the accepted control listener and creates one `CpSession` per socket. `CpSession` owns one `CpStack`. `CpStack.attachSocket` decrypts/parses RTSP, serializes requests, dispatches `/info` and SETUP, writes responses, and tears down stream resources. `CpHelperSock` calls the helper's Unix socket `/tmp/cp-bt.sock` for MFi certificate/sign and iAP2/BlueZ-related operations. It is a signer/helper API, not a control request/response handoff.

The exact source symbols and lifecycle are traced in [architecture map](r6g-livi-carplay-architecture-map.md). The upstream project is GPL-3.0-or-later; ClarityLink has not copied or linked LIVI implementation code. Any future distribution of an integrated LIVI patch/build needs a GPL compatibility and distribution review. The Python adapter here speaks only a proposed local delegate contract; it does not load LIVI or establish authentication.

## Review limits

Public source review establishes implementation structure at the pinned commit, not that CPC200 inventory, provisioning, MFi provenance, iPhone authentication, or Type111 behavior works on this Mac. Upstream `main` can change; re-pin and re-review before any source patch or hardware provisioning.
