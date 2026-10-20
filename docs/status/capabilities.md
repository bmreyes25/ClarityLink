# Capability and evidence matrix

| Capability | Current claim | Evidence boundary |
|---|---|---|
| Stock Type110 path | Examined in archived Honda evidence | Claim scope is in the [evidence index](../../EVIDENCE_INDEX.md); does not imply Type111 acceptance. |
| Binder-to-View lab path | API17 laboratory verified | Separate-process Binder/PFD frames rendered to the API17 View; warning handling and crash recovery are lab evidence only. See the [CL-R3 acceptance summary](../../research/vehicle/test6a-t7-integration/22-cl-r3-final-acceptance.md). |
| Type111 decoder and transport | Partial API17 laboratory integration | H.264 fixture decoding, Binder/PFD delivery, and View output are demonstrated; producer/sink reconnection and full parent-owner fault closure remain incomplete. See the [tracked stream-isolation result](../../research/vehicle/test6a-t7-integration/26-cl-r4-stream-isolation-results.md) and [process-isolation receipt](../../research/vehicle/test6a-t7-integration/28-type111-process-isolation-runtime.md). |
| Authenticated Type111 delegation | Unproven | No genuine Honda same-session delegation established. |
| Honda cluster frame output | No supported frame interface found in reviewed evidence | HondaHack is an in-process precedent, not an independently supported interface. |
| Vehicle-ready integration | No | `safeForHonda()` is false; no installation or vehicle validation is authorized. |

Evidence references and dated detail are in [current status](current.md) and the numbered [Test 6A/6B/7 reports](../../research/vehicle/test6a-t7-integration/).
