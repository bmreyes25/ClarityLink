# 43T1-R3A — Setup path and seam map

**Scope:** repository evidence map only. The named addresses and flow are bounded to the hash-matched Honda `jmcs` artifact and source reports. This map does not authorize runtime access or imply that a candidate is callable by ClarityLink.

## Known path

| Setup path step | Evidence location | Seam position | Evidence label | Assessment |
|---|---|---|---|---|
| Request parse / message dispatch in `_connectionHandleMessage` | `step-reports/43l-post-setup-transaction-seam.md`; `research/carplay/honda-post-setup-existing-call-map.md` | before response construction | `HONDA_CONFIRMED` | Handler entry exists; no supported external handler registration/dispatch wrapper is evidenced. |
| `AirPlayReceiverSessionSetup` parses request and extracts streams | Same sources; `0x28af72` call noted in 43L/R2 records | before response construction | `HONDA_CONFIRMED` | Direct internal call. R2 rejects patching the straddled Thumb BL under unresolved stop/restoration assumptions. |
| Response dictionary and stock response construction | 43L report and R2 CFLite ownership audit | during response construction | `HONDA_CONFIRMED` | Existing response graph is Honda-owned. External insertion point is not established. |
| `_AddResponseStream` creates/obtains streams array and appends stream entry | `research/carplay/honda-post-setup-existing-call-map.md`; 43L report | during response construction | `HONDA_CONFIRMED` | Construction helper is internal; no registration/callback seam evidenced. |
| `streams` array creation and stock entries | R2 report; `research/runtime/honda-cflite-ownership-static-audit.md` | during response construction | `HONDA_CONFIRMED` | Ownership facts cover observed stock graph and do not establish arbitrary Type111 entry semantics. |
| Success metadata and response staging | 43L map; caller context around `0x28afae–0x28afb8` | before serializer | `HONDA_CONFIRMED` | Caller has useful context, but callout safety is not proven. |
| `_requestSendPlistResponse` call | `step-reports/43m-existing-call-wrapper-seam.md`; `research/carplay/honda-request-send-plist-wrapper-audit.md` | before serializer | `HONDA_CONFIRMED` | Direct local Thumb BL; no supported wrapper route shown. Interception requires a code redirect under current evidence. |
| `CFPropertyListCreateData` serializes response | 43M wrapper audit; R2 report | during serializer | `HONDA_CONFIRMED` | Shared lower-level operation; no Setup-scoped mediation demonstrated. Apple CF reference material is not Honda runtime proof. |
| `HTTPMessageSetBody` installs serialized bytes | 43M wrapper audit | after serializer | `HONDA_CONFIRMED` | Too late to safely alter the response dictionary as a typed entry. |
| Serializer return/status check | 43L/43M path map (`r0 == 0xc8 && statusOut == 0`) | after serializer | `HONDA_CONFIRMED` | Local result is observable in caller; no independent callback is evidenced. |
| Response release | 43M map; caller cleanup at `0x28b052` | after serializer | `HONDA_CONFIRMED` | Response object lifetime ends in common cleanup; mutation opportunity has passed. |
| Later `HTTPConnectionSendResponse` | 43M report | after serializer | `HONDA_CONFIRMED` | Send is later than serialization and response release; unsuitable for response graph mutation. |
| Session cleanup / `_Finalize` / `PlatformFinalize` | `step-reports/43l2-session-finalizer-extension-audit.md`; `research/carplay/honda-project-child-cleanup-reachability.md` | cleanup/finalizer | `HONDA_CONFIRMED` | Cleanup path exists, but complete failure coverage and project-child subscription are not evidenced. |
| Any supported plugin/load route | `step-reports/41f-honda-linker-preload-fingerprint.md`; `research/runtime/jmcs-load-seam-audit.md` | outside jmcs | `UNKNOWN` | Current preserved evidence does not demonstrate a supported extension route. Generic API-17 loader documentation cannot fill this gap. |
| External process/proxy mediation | architecture only | outside jmcs | `INFERENCE` | Reject if it entails authentication breakage, USB injection, MITM, manual phone traffic manipulation, or persistent Honda changes. |

## Path sketch

```text
request parse / stream extraction
  → response construction
  → _AddResponseStream / streams array
  → response metadata and staging
  → _requestSendPlistResponse
  → CFPropertyListCreateData
  → HTTPMessageSetBody
  → serializer result/status
  → response release
  → HTTP response send
  → session cleanup/finalizer
```

The useful response-context interval is statically visible. No evidence reviewed here turns that interval into a supported non-inline entry. Inline callsite patching remains rejected by R2. Cleanup study is a separate lifecycle prerequisite, not a substitute for response mediation.
