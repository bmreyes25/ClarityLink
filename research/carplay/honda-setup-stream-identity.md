# Honda SETUP stream identity trace — Step 43D

**Step 43E update:** The response lifetime and post-Setup/pre-serialization structural seam are now audited separately from `/info` and stream identity. See [Honda post-Setup response seam](honda-post-setup-response-seam.md) and [Step 43E](../../step-reports/43e-post-setup-response-seam.md). The seam is a safe static candidate for offline study only; response/array post-return mutability remains indirect, and implementation readiness is NO. This does not change the unknown UUID-to-stream identity relation or Type111 schema.

**Evidence:** `HONDA_CONFIRMED` static analysis of the matching `jmcs` ELF only. No vehicle, ADB, runtime, or Type111 implementation was used. ELF SHA-256: `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

## Honda request path

`_connectionHandleMessage` parses the request body as a property-list dictionary and calls `AirPlayReceiverSessionSetup` (`0x2854e0`). Setup obtains `streams[]`, iterates its dictionaries, and reads each `type` using `CFDictionaryGetInt64` at `0x28590e`.

For type 110, the inlined `_ScreenSetup` reads `streamConnectionID` as a 64-bit integer using `CFDictionaryGetInt64` at `0x2860a8–0x2860b2`. Zero is rejected. The local value is passed to `AirPlay_DeriveAESKeySHA512ForScreen` at `0x2860c4–0x2860d2` with the receiver-session 16-byte master material. The ID is therefore confirmed as an input to Type-110 screen crypto derivation. The available trace does not prove that this ID is stored as a persistent named field or that it selects the display UUID.

`AirPlayReceiverSessionScreen_Setup` is called at `0x28609c`; it performs a separate CFL dictionary lookup and stores two returned words at Screen object offsets `+0x10` and `+0x14`. The lookup key and the semantic meaning of these words remain unresolved. They must not be labeled `streamConnectionID`, display UUID, or screen role.

### Request fields recovered

| Request key | Function / address | Object field written | Type / width | Use | Confidence | Display identity relation |
|---|---|---|---|---|---|---|
| `streams` | `AirPlayReceiverSessionSetup`, around `0x2858xx` | Local array/count/index state | CFL/CF array object | Iteration over requested stream entries | High | None established |
| `type` | `AirPlayReceiverSessionSetup`, `0x28590e` | Local dispatch value | `CFDictionaryGetInt64` integer | Routes 100/101 audio, 110 screen; unsupported values logged/skipped | High | Selects stream setup branch; no `/info` display role link shown |
| `streamConnectionID` | Inlined `_ScreenSetup` in Setup, `0x2860a8–0x2860d2` | Local 64-bit value passed to screen KDF; persistent storage not established | nonzero `uint64_t` | Type-110 key/IV derivation | High | No UUID/index/HID relation found in traced path |
| Screen_Setup's other CFL key | `AirPlayReceiverSessionScreen_Setup`, reached at `0x28609c`; helper `0x294598` | Screen object `+0x10`, `+0x14` | Returned word pair; semantic types unresolved | Screen setup state | High for dataflow, unknown meaning | No proven UUID or stream-ID identity |

No other requested keys from the proposed candidate list are included here because the Honda paths inspected do not establish them as stream-dictionary reads. In particular, `timingProtocol`, `timestampInfo`, `latency`, geometry, `uuid`, `displayUUID`, `screenUUID`, `features`, `viewArea`, `initialViewArea`, `initialURL`, and `primaryInputDevice` are not proven reads in the recovered Type-110 stream-descriptor path. This is scoped non-recovery, not proof that the whole protocol lacks those fields.

## Honda response path

`AirPlayReceiverSessionSetup` creates a mutable response dictionary. `_AddResponseStream` (`0x284db8`) obtains or creates the `streams` array, appends a response entry, then stores that array on the response. The successful response pointer is returned at `0x286260`; `_connectionHandleMessage` passes the same response to `_requestSendPlistResponse` (`0x289f60`), which serializes it synchronously. See [response serializer evidence](honda-response-serializer.md).

In the Type-110 branch, Honda opens a TCP listener with requested port 0 at `0x286124`. The resulting listener port is inserted with the constant `type=110` in the appended response stream at `0x28614a–0x286168`.

| Response key | Function / address | Value source | Request copy? | Generated / constant? | Phone-facing? | Confidence |
|---|---|---|---|---|---|---|
| `streams` | Setup + `_AddResponseStream` `0x284db8` | Mutable array accumulated in response | No; response container | Generated | Yes, serialized via response path | High |
| `type` | Type-110 response builder, `0x28614a–0x286168` | Literal/integer 110 | No; inserted by Honda | Constant for this branch | Yes | High |
| `dataPort` | Type-110 response builder, after `ServerSocketOpen` `0x286124` | Bound listener's selected ephemeral port | No; generated from listener | Runtime-generated | Yes | High |
| `streamConnectionID` | No insertion observed in this response builder | None recovered | Not observed | Unknown outside this entry | No response echo proven | High for this builder only |
| `timingPort`, `eventPort`, timing/latency fields | No insertion observed in recovered Type-110 entry | None recovered | Unknown | Unknown outside this response builder | Not shown in this entry | Scoped non-recovery |
| Display UUID / display index | No insertion observed in recovered entry | None recovered | Not observed | Unknown elsewhere | Not shown in this entry | High for this builder only |

The response stream entry evidence is `{type: 110, dataPort: assigned_port}`. This describes the recovered Type-110 entry, not every field in the enclosing Setup response or all ancillary streams.

## Type dispatch

| Type | Honda path | Response consequence | Evidence |
|---|---|---|---|
| 100 / 101 | Audio setup branch | Audio-specific; exact entries are outside this screen trace | `AirPlayReceiverSessionSetup` dispatch |
| 110 | Screen setup | Reads nonzero uint64 `streamConnectionID`, derives/installs screen crypto, starts listener, appends `{type:110,dataPort}` | `0x28606e` onward; Step 34 / Step 38 records |
| 111 / other unsupported values | Unsupported log at `0x2861f6`, then common loop increment `0x286220` | No Type-111 response entry; the unsupported branch itself does not set an error or roll back other entries | `research/carplay/honda-mixed-stream-setup.md` |

This is Honda stock behavior in the analyzed binary. It does not establish whether or how an iPhone will request a secondary stream.

## Identity correlation result

The recovered `/info` path advertises a main display descriptor whose `uuid` is a numeric Screen property. The Type-110 Setup path reads `type` and `streamConnectionID`; the latter enters screen crypto derivation. In the analyzed paths, no display UUID, display index, HID `displayUUID`, or Screen UUID comparison is shown in the Setup stream code; no streamConnectionID is shown in the display descriptor builder.

| Relationship | Honda status |
|---|---|
| Setup `type` → stream branch | `HONDA_CONFIRMED` |
| Type-110 `streamConnectionID` → screen crypto input | `HONDA_CONFIRMED` |
| Type-110 listener → response `dataPort` | `HONDA_CONFIRMED` |
| Request `streamConnectionID` echoed in response | Not observed in recovered entry |
| `/info` display UUID → Setup type or connection ID | `HONDA_UNKNOWN` (no binding found in paths traced) |
| Screen object offsets `+0x10/+0x14` → UUID or connection ID | `HONDA_UNKNOWN` (lookup key/meaning unresolved) |
| Display UUID role as presentation vs HID/input identity | `HONDA_UNKNOWN` for Honda |

**Honda model:** `MODEL_D_INSUFFICIENT_EVIDENCE` for the semantic identity relationship. The best search model is to treat `/info` display capabilities and Setup media-stream entries as separate layers until evidence connects them. A distinction between the parsed Setup `type` and the crypto input `streamConnectionID` is directly Honda-confirmed. Any stronger claim that UUID is an input/display identity or that an iPhone will choose Type111 from a particular advertisement remains external prior art or hypothesis.

## Bounded solution hypothesis

`HYPOTHESIS`: if Honda's phone-facing capability exchange can be safely extended and the iPhone requests a secondary stream, a stock-first design would leave Type-110 processing and response untouched, then handle only a requested Type 111 and maintain separate listener/crypto state. The response shape, descriptor-preservation policy, required fields, Type-111 connection-ID semantics, and whether existing Honda crypto can be reused remain unknown. MHI2's clone/append approach is only prior art for its own target.

No Type111 code was implemented. No live gates changed.

## Inputs and source records

- [Honda SETUP request parsing](honda-setup-request.md)
- [Honda SETUP response and append boundary](honda-setup-response.md)
- [Honda `streamConnectionID` / crypto trace](stream-connection-id.md)
- [Honda display-stream correlation](display-stream-correlation.md)
- [Honda mixed-stream behavior](honda-mixed-stream-setup.md)
- [External prior-art identity model](setup-stream-identity-prior-art.md)
- [Step 43D report](../../step-reports/43d-setup-stream-identity-correlation.md)
