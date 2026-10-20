# R6G LIVI control-session seam

## Finding

At pinned LIVI commit `dcb78854c59ba621f4d327910dc275da386496b4`, the narrowest workable seam is in `CpStack.attachSocket`'s ordered request loop, immediately before `this._handle(req, session)`. The loop already has the decrypted `RtspRequest`, the live private session, and owns the one `buildResponse` + socket write. A delegate there can receive method/path/header metadata and decoded plist body, return one `RtspResponse`, and leave encryption, RTSP serialization and socket ownership with LIVI.

The stock `_handle` is private and directly owns `/info`; `_handleSetup` is private and performs listener/stream side effects as well as response construction. `CpHelperSock` exposes MFi signer/helper operations, not a control-session stream. No supported public delegation API was found.

## Required classification

**`R6G_LIVI_CONTROL_DELEGATION_SMALL_PATCH`**. The request/response ownership is a bounded dispatch change rather than a new CarPlay implementation. However the patch is not present upstream and has not been exercised against an iPhone. A clean adapter requires an explicit supported delegate contract, not monkey-patching private methods.

## Delegate contract

The upstream patch should add one optional `ControlSessionDelegate` set at `CpManager`/`CpSession` construction. It may expose only:

- `onAuthenticated(metadata)` once LIVI's own MFi/iAP2/pair verification gate succeeds; metadata is a new opaque generation and capabilities, with no phone identifiers or secrets.
- `onRequest(request)` for `/info` and SETUP before either stock handler runs. Request contains method, path, allowlisted headers, content type and bounded decoded plist body.
- `writeResponse(response)` or a returned `RtspResponse`, correlated to the outstanding request. The stack's existing `buildResponse` and socket writer are the only serializer/writer.
- `onDisconnect(reason)` to close the ClarityLink handoff and invalidate generation.

No MFi key, certificate private data, pairing secret, challenge bytes, encryption key, raw phone identifier, socket, or private `CpStack` session object crosses the boundary. Use one in-flight request at a time (matching LIVI's promise chain), an explicit timeout and body/node bounds. Delegate errors fail closed to one sanitized 5xx response and terminate the session; no fallback to the stock `/info` or SETUP handler after ClarityLink has claimed ownership.

## Type111 / SETUP caveat

The seam is early enough for ClarityLink to choose the `/info` and SETUP response. But stock SETUP also creates timing/event listeners and stock stream listeners. The patch must gate those side effects when delegated. The first integration should delegate `/info`; the SETUP route must remain disabled until ClarityLink can own its control response and listener consequences. This is a compatibility concern for R6H, not a reason to duplicate or proxy the serialized response.

## Classification of alternatives

| Candidate | Result | Reason |
|---|---|---|
| `CpHelperSock` JSON RPC | `NOT_USABLE` as control handoff | Signer/helper/iAP2 functions, not RTSP requests/responses |
| `CpManager.onSpawn` / `CpSession` events | `NOT_USABLE` alone | Driver/media lifecycle callbacks do not own request dispatch |
| `CpStack` request loop before `_handle` | `SMALL_UPSTREAM_PATCH_SEAM` | Has decoded request and single response writer before stock handler |
| Post-response listener/proxy | `NOT_USABLE` | Too late to author `/info` or insert Type111 in SETUP |
| Reflection/monkey-patch private `_handle` | `INVASIVE_FORK_REQUIRED` | Unstable private internals, no exclusive ownership guarantee |
