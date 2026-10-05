# R6A receiver reuse / replace matrix

Verdicts describe engineering direction, not proven target interoperability. Evidence classes remain scoped as in [rules v2](../../docs/project/claritylink-rules-v2.md).

| Subsystem | Current stock owner | Evidence | Can reuse stock? | Can reuse library/API? | Must ClarityLink implement? | Adapter needed? | Current blocker | Confidence / verdict |
|---|---|---|---|---|---|---|---|---|
| USB | Unknown | [substrate audit](r6a-honda-receiver-substrate-audit.md) | Unknown | Unknown | Maybe | Yes | owner/interface | low / EVIDENCE_REQUIRED |
| iAP2 | Unknown | substrate audit | Unknown | Unknown | Maybe | Yes | session handoff | low / EVIDENCE_REQUIRED |
| MFi/auth | Unknown | substrate audit | Unknown | Unknown | Maybe | Yes | hardware/API | low / EVIDENCE_REQUIRED |
| CarPlay session | jmcs | [R3C](../../step-reports/43t1-r3c-static-entry-ownership-closure.md) | No complete seam | No demonstrated API | Yes | Yes | authentication/transport | high / REIMPLEMENT |
| /info | jmcs | [Honda info](../carplay/honda-copy-displays-info.md) | No additive seam | Unknown | Yes | Yes | full iPhone profile | high / REIMPLEMENT |
| SETUP | jmcs | [R5Z graph](r5z-honda-receiver-callgraph.md) | No additive seam | Unknown | Yes | Yes | real session context | high / REIMPLEMENT |
| Type110 | jmcs | R5Z graph | No as separate stock stream | Possibly media libraries | Yes | Yes | stock equivalence | high / REIMPLEMENT |
| Type111 | absent in inspected jmcs | R5Z graph | No | Unknown | Yes | Yes | real negotiation/security | high / REIMPLEMENT |
| screen security | jmcs Type110 | [crypto](../carplay/honda-screen-crypto.md) | Unknown | Unknown | Yes | Yes | authorized keys/context | medium / EVIDENCE_REQUIRED |
| primary listener | jmcs | R5Z graph | No | socket API | Yes | Yes | target bind policy | high / REIMPLEMENT |
| secondary listener | absent | R5Z graph | No | socket API | Yes | Yes | same session ownership | high / REIMPLEMENT |
| ScreenStream framing | jmcs Type110 | [framing](../carplay/honda-screen-framing.md) | No | Unknown | Yes | No | current Type111 bytes | medium / REIMPLEMENT |
| H264 decoder | Honda media stack | [decoder path](../carplay/decoder-output-path.md) | Unknown | libstagefright possible | Yes host; target adapter | Yes | target codec API | low / REUSE_ADAPTER |
| audio | jmcs / Android media partial | substrate audit | Unknown | Possible | Yes if session coupled | Yes | route and ownership | low / EVIDENCE_REQUIRED |
| controls | Honda proxy/services partial | substrate audit | Unknown | Possible | Yes event mapping | Yes | input contract | low / EVIDENCE_REQUIRED |
| Display0 | jmcs / media partial | substrate audit | No screen ownership handoff | Possible Surface | Yes output contract | Yes | exact sink | low / EVIDENCE_REQUIRED |
| Display1 | ExternalDisplayOutService | [R4C](43t1-r4c-honda-display1-ownership-audit.md) | No arbitrary frame endpoint | Android display APIs possible | Yes | Yes | admission/warnings | medium / REUSE_ADAPTER |
| teardown | jmcs | [R3C](../../step-reports/43t1-r3c-static-entry-ownership-closure.md) | No Type111 path | No | Yes | Yes | target lifecycle | high / REIMPLEMENT |
| service lifecycle | init/jmcs unknown | [startup](jmcs-startup-path.md) | Unknown | Unknown | Yes | Yes | init/watchdog contract | low / EVIDENCE_REQUIRED |
