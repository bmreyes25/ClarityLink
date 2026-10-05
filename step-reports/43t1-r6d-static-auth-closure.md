# 43T1-R6D — final bounded static factory authentication closure

Date: 2026-10-04. Starting main HEAD: `6d0c798f8b1f9821d0b7532a203266ab585db727` (R6C PR #6 merge). Branch: `architecture/r6d-static-auth-closure`; worktree: `../clarity-r6d-static-auth`, created clean from that commit. Implementation HEAD and final verification HEAD are the PR head reported at completion; this report is part of that commit. No pre-merge R6C lineage was reused. The preserved `jmcs` and `libcarplay_proxy.so` hashes matched R6C before static inspection.

## Result and exact boundary

| Question | Bounded answer and evidence |
|---|---|
| USB/iAP2 owner | `jmcs` USB host and `ios_iap2` in the same ELF; exact USB fd untraced. [Ownership](../research/runtime/r6d-auth-session-object-ownership.md) |
| Authentication owner | `jmcs` auth callbacks and configured factory I²C path; hardware not accessed. [R6C](../research/runtime/r6c-honda-mfi-auth-owner.md) |
| Authenticated transition | `auth_result` calls `ios_iap2_set_authenticated`, which marks iAP2 owner context and invokes generic `do_attach`; direct `mc_ios_dev_attach` → `mc_carplay_attached` follows on the device side, with indirect dispatch unresolved. [Transition](../research/runtime/r6d-iap2-to-airplay-transition.md) |
| AirPlay receiver owner | `_AirPlayThread` created separately during `mc_carplay_app_init`; it creates server and a connection later creates `AirPlayReceiverSession`. [Call graph](../research/runtime/r6d-authenticated-session-transition-callgraph.md) |
| Control transport | Internal AirTunes connection/handler and synchronous `/info`/SETUP plist response path. [Control owner](../research/runtime/r6d-airplay-control-transport-ownership.md) |
| Security context | Connection-local SAP exchange/decrypt installs master material in session; Type110 derives from that session plus stream ID. Direct iAP auth-to-SAP relationship unknown; Type111 unknown. [Security](../research/runtime/r6d-airplay-security-context-source.md) |
| External factory-auth API | No supported external consumer contract found in reviewed ELF, proxy, Binder or service surfaces. [Boundary audit](../research/runtime/r6d-authenticated-session-boundary-audit.md) |
| External authenticated-session API / transferable object | None found with request, response, identity, security and close ownership. Internal pointers/fds are not transferable APIs. [Decision matrix](../research/runtime/r6d-factory-auth-handoff-decision-matrix.md) |
| `libcarplay_proxy` | Process-local singleton auth/audio/screen callback facade; no external control session. [Proxy closure](../research/runtime/r6d-libcarplay-proxy-boundary-closure.md) |

Authentication-boundary decision: **`R6D_NO_SUPPORTED_FACTORY_SESSION_HANDOFF`**. Proxy decision: **`R6D_PROXY_IN_PROCESS_ONLY`**. Custom-receiver architecture decision: **`R6D_CUSTOM_RECEIVER_REQUIRES_INDEPENDENT_AUTH_TRANSPORT`** for the next host proof. The R6C `ARCH_A/B/E/UNKNOWN` labels have no formal definitions in tracked architecture documents beyond informal R6C usage; R6D does not assign them new meanings. It makes the bounded supported-interface decision above. [Receiver impact](../research/runtime/r6d-custom-receiver-auth-impact.md) preserves the future target distinction.

No Honda adapter was extended: its `EVIDENCE_REQUIRED` result is correct. Next: **`GO_FOR_R6E_CUSTOM_RECEIVER_AUTH_TRANSPORT`** — integrate an authorized MFi hardware/service owner with a structured authenticated control-session handoff on Mac, then attempt a real iPhone `/info` exchange. This is an engineering task with a concrete first gate, not more generic Honda firmware research.

## Safety and verification

Honda contacted: **NO**. ADB used: **NO**. Vehicle connected: **NO**. Runtime reads/writes: **NONE**. I²C/authentication hardware accessed: **NO**. Secrets extracted: **NO**. `jmcs` modified: **NO**. No key, certificate, auth blob, VIN, MAC, private capture or Honda binary is committed. Inspection was static disassembly/symbol review of ignored local preserved files only.

Focused R6B/R6C adapter tests: **12 passed**. Full offline suite: **857 passed, 14 skipped**, plus self-locator smoke and simulator checks. Repository health: **614 Markdown files, 134 indexed reports, 0 broken curated links, 0 forbidden tracked extensions**. `git diff --check` passed. Offline CI and CodeQL will be checked on the pushed implementation/final verification HEAD; pending hosted results are not presumed green.
