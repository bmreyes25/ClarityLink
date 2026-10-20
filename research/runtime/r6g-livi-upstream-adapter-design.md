# R6G LIVI upstream adapter design

## Status

The ClarityLink Python provider is implemented at `claritylink_jmcs.auth_providers.livi`. It implements the existing `AuthorizedAuthenticationAuthority` → `AuthenticatedSessionHandoff` → `CarPlaySessionTransport` boundary and is ready to bind to a reviewed LIVI delegate bridge. It does not itself authenticate a phone. The upstream change remains a small patch requirement; no LIVI source has been copied into ClarityLink and no upstream patch was silently applied.

## Bridge responsibilities

LIVI remains the sole owner of USB/network/iAP2, genuine MFi operations, pairing/encryption, RTSP socket, parser, response serializer and disconnect. Its delegate must claim `/info` and SETUP before stock `_handle`, and the response must be returned once through LIVI's existing `buildResponse` + socket writer. Delegated requests must not invoke stock handlers or stock stream side effects. If a request is unclaimed, the stock handler may serve only routes ClarityLink has not claimed.

The bridge factory implements `open_authenticated(generation)`. It may return only after LIVI has asserted its authenticated session state and selected a delegated control channel. The bridge implements `authenticated`, opaque `session_identifier`, `generation`, `read_request(timeout)`, `write_response(response)` and `close()`. The Python adapter verifies all three identity/lifecycle values and delegates bounds to the existing structured control validator. It never receives cryptographic material.

## Lifecycle / protocol requirements for upstream implementation

1. Allocate a fresh monotonically increasing local generation for every accepted authenticated session.
2. Emit one authenticated-session event only after the LIVI-owned MFi/iAP2/pairing path succeeds. Do not infer auth from a TCP accept, socket address, `/info`, or synthetic fixture.
3. Maintain a single outstanding request/response and preserve the RTSP request CSeq/headers internally for the serializer. The bridge returns only a `ControlResponse`; ClarityLink never writes to LIVI's socket.
4. Enforce 1,000,000 byte body limit, 12 levels, 4096 structured nodes, 256 map/array entries, 4096 character strings, and 30-second maximum wait before the bridge boundary. Close on malformed, stale-generation or uncorrelated response.
5. In delegated mode, make ClarityLink the only `/info`/SETUP responder. Disable stock response and stream setup for those requests. A ClarityLink exception cannot trigger stock fallback.
6. On close/disconnect/timeout, invalidate the generation, close ClarityLink transport and notify one disconnect callback. Reconnect uses a new session and generation.
7. Keep logs to method/path, allowlisted header names, content type, sanitized generation, plist key paths/types/counts and result status. Never log request body values, identity fields, pairing/auth values or raw peer address.

## Integration boundary decision

No TCP/HTTP listener is opened by this provider and no network bind is needed. The expected LIVI delegate can use an in-process callback initially; a process boundary is required only if LIVI and ClarityLink remain separate processes. If IPC is used, prefer a permission-restricted local Unix socket with peer-UID validation and length-prefixed or bounded framed messages; no wildcard bind. The actual upstream source currently has no delegate or IPC protocol, so there is no live bridge to load yet.

## Dependency / patch discipline

LIVI is GPL-3.0-or-later. This repository contains no vendored LIVI code or patch. A future upstream patch must pin the same upstream base, include exact changed files and tests, and receive a license/distribution review before bundling. The `LiviBridge` protocol in Python is ClarityLink-owned adapter code, not an assertion that LIVI currently implements it.

## Test meaning

Provider lifecycle tests use a clearly named test-only bridge to exercise shape, generation, timeout, redaction and cleanup. They are synthetic contract tests only; they prove no authority or real-iPhone milestone. Before hardware, a real LIVI bridge integration test is still required.
