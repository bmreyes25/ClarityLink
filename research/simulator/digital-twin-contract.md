# Digital twin contract for Step 42C

| Entity | Twin representation | Evidence class |
|---|---|---|
| Honda center Type110 | Stock response, lifecycle and synthetic media/render path | Honda fields plus synthetic values |
| Type111 secondary | Independent generation/listener/crypto/parser/codec; candidate response | MHI2 hypothesis plus synthetic values; Honda support unknown |
| jmcs session | Opaque handle, Setup request/result, lifecycle events | Owner Honda-confirmed; handle synthetic |
| Vehicle state | Fake speed/gear/navigation/display availability | Synthetic; no CAN/live state |
| Display/stream descriptors | Honda baseline plus separate candidate profile | Honda facts vs MHI2 hypothesis |
| Renderer/ExternalDisplay | Mock Display 1 backend and host attach state | Synthetic; not Android composition |
| Errors/timeline | Typed failure events, monotonic timestamps, bounded memory log | Synthetic |

Evidence labels:
- HONDA_CONFIRMED_FIELDS: Type110 type/ID/dataPort and stock /info key/container shape. Values are synthetic unless from approved non-sensitive evidence.
- MHI2_DERIVED_HYPOTHESES: candidate Type111 streamID, cloned fields, listener order and security reuse.
- SYNTHETIC_TEST_FIELDS: generated IDs, ports, master bytes, frames, time and failures.
- UNKNOWN_FIELDS: Honda Type111 response, UUID correlation, KDF, feature negotiation, phone connect ordering and render handoff.

Unknown identity never defaults to a Honda UUID. Unknown Type111 requirements fail closed.

Assertions: stock response immutable; Type110/audio order and values preserved; Type111 crypto/parser state generation-isolated; secondary-only failure does not reset Type110; parent teardown closes child; renderer accepts frames only for active generation and clears on teardown; every test labels evidence class.

The twin can test state transitions, bounds, rollback, generated crypto isolation and renderer lifecycle. It cannot prove phone acceptance, MFi/iAP2 authentication, Honda Type111 wire/key compatibility, code entry, Binder access, physical Display 1 geometry or live center-display preservation.
