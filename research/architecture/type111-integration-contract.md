# Type 111 integration contract — candidate only

| Output | Honda confirmed | MHI2 hypothesis | Unknown for Honda | Preserve Type110 |
|---|---:|---:|---:|---:|
| Optional second /info descriptor | No; stock emits one | Second descriptor used by prior art | Fields, capability generation, iPhone acceptance | Yes |
| Type111 Setup response | No; Honda skips request | MHI2 clones requested descriptor, adds dataPort and streamID=111 | Exact fields and peer acceptance | Yes |
| Type111 dataPort/listener | No | Separate listener | Transport and lifetime | Yes |
| Type111 streamConnectionID | No handler | MHI2 uses an ID | Source/constraints | Yes |
| Security binding | No | MHI2 session material plus stream ID/context | Master reuse/KDF/authentication | Yes |
| ScreenStream/config parser | Type110 evidence only | Possible protocol similarity | Type111 framing/opcode compatibility | Yes |
| VideoConfig/H.264 pipeline | Type110 path recovered | Reuse plausible | Codec/config/timing variants | Yes |
| Decoded frame submission | No Honda Type111 path | Separate output in prior art | Adapter API/format/geometry | Yes |
| Status/error behavior | No ClarityLink API | Implementation-specific | Logs and peer behavior | Yes |

Current candidate response fields are MHI2-derived and are not endorsed as Honda wire fields.

Failures must be stock-first and fail-soft: no project resources on stock Setup failure; malformed candidate means stock-only response; project listener/KDF/serialization failure closes only project resources; Type111 disconnect clears only its own state; parent-session teardown closes the child.
