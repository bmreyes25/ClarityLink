# R7C1 fault-injection matrix

| Fault | Environment/result | Scope / limitation |
|---|---|---|
| Unavailable production authentication/security | PASS, rejected before `/info`/media | Receiver fail-closed path. |
| Type111 sink lock/display unavailable | PASS, Type111 ingest fails; Type110 frame remains active | Host fake window. |
| Type111 surface invalidated after a frame | PASS, later secondary frame rejected, Type111 resources released, Type110 continues | Host core invalidation after successful decode; invalid surface is no longer presented. |
| Type111 malformed media/decode | PASS, Type111 resources removed; Type110 continues | Synthetic test packet and real host decoder. |
| Type110 primary surface unavailable | PASS, session transitions to `Closed`; both stream resources zero | Host fake window; model primary policy. |
| Post-close frame / stale generation / wrong stream | PASS in receiver and surface-core tests | Host model. |
| Surface geometry/lock/post failure | PASS | Host backend fault flags. |
| Surface replace/invalidate during a frame | PASS | CV-controlled host fake; no real ANativeWindow. |
| Socket loopback, wildcard bind, port conflict, generation, peer close | PASS separately under ASan/UBSan and TSan | Existing socket test, not the all-adapter harness. |
| JNI invalid/stale/double handle, concurrent allocation/erase | PASS under ASan/UBSan and TSan | Shared production table/allocator template; no real VM. |

Not covered by a complete deterministic integrated matrix: process initialization/allocation faults, actual Java Surface callback and exceptions, actual Presentation admission, socket accept/timeout/partial I/O within the same harness, Android audio open/write failure while decoding, Java input callback close races, USB permission/device/endpoint failure in Android runtime, iAP2/auth provider implementation failures after session startup, JNI callbacks during native shutdown, and every requested stop-at-/info/SETUP/decode/socket/audio callback race. These remain R7D software-entry blockers. They are not silently treated as passes.

Type111 stream-local faults: display/surface delivery failure, malformed media/decode failure, and secondary setup failure. Type110 primary surface/decode failure: session-global; tear down both streams and close. Session authentication and process-global shutdown are session-global.
