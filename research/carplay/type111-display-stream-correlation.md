# Step 42A — display and stream correlation

**Scope:** offline static analysis of the identity-verified Honda `jmcs` analysis already recorded in this repository, plus checked-in Android package manifests/decompiled sources. No ADB, vehicle, firmware modification, Type 111 implementation, or proprietary capture was used for this audit.

## Evidence-bounded Honda Type 110 path

| Object | Honda-confirmed shape and values | Boundary |
|---|---|---|
| `/info` display collection | `serverInfo["displays"]` is a CFArray; `AirPlayCopyServerInfo` puts the platform `displays` property into the object returned by `_requestProcessInfo`, which is passed to the binary-plist serializer and HTTP send path. | Static code dataflow confirms phone-facing serialization; this is not a wire capture. See [Step 32](../../step-reports/32-airplay-info-phone-path.md). |
| Display descriptor builder | `AirPlayReceiverSessionScreen_CopyDisplaysInfo` creates one mutable CFDictionary, calls `ScreenCopyMain()` once, and inserts properties. The platform property callback appends that one dictionary to the `displays` array. | The stock builder is singleton in its observed path. It does not enumerate displays. See [descriptor recovery](honda-copy-displays-info.md). |
| Descriptor fields | Literal keys: `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels`, `uuid`. The recovered `uuid` insertion uses a numeric CF setter; runtime value and semantic identity rules remain unknown. | Field presence/insertion is confirmed; value semantics and exact iPhone interpretation are not. |
| Setup stream request | `streams[]` entry's integer `type` is read. For type 110, the branch reads nonzero uint64 `streamConnectionID`; no display UUID read or comparison was found in that branch. | Honda confirms these reads for Type 110 only. |
| Setup stream response | The Type 110 path appends `{type: 110, dataPort: assignedPort}` to a mutable `streams` array. `dataPort` is from its ephemeral TCP listener. The request `streamConnectionID` is not shown in this response dictionary. | Honda-confirmed static response construction and serialization; no display correlation key appears in this entry. |
| Security | Type 110 derives 16-byte screen key and IV from session master material and the uint64 ID, initializes a dedicated AES-CTR state on the screen object, then opens the listener. | Exact Type 110 derivation is in [security contract](type111-security-fields.md). |

## Correlation result

No Honda object, field access, or recovered code path joins display `uuid` to `streamConnectionID`. `uuid` is not read by the analyzed Type 110 Setup branch; the ID is not read by the display descriptor builder. The assigned listener and returned `dataPort` bind the accepted TCP connection to that listener, but do not explain why the phone selected a display for a given request.

```text
DISPLAY UUID -> streamConnectionID: UNKNOWN / no Honda link recovered
streamConnectionID -> screen crypto: HONDA CONFIRMED for Type 110
Type 110 response -> dataPort listener: HONDA CONFIRMED
Type 110 response -> display UUID: no link found
Type 111 -> display: unsupported request entry is skipped; no Honda response entry
```

The display collection is an array and can structurally hold more than one dictionary, but Honda's stock property callback inserts one descriptor produced by `ScreenCopyMain()` exactly once. Thus the **container shape is multi-entry capable; the stock display construction path is single-display**. This distinction does not prove that an iPhone accepts an appended second descriptor.

Setup's response is also an array and can contain successful entries for the handled stream types. The dispatcher handles 100/101 and 110. Type 111 follows the unsupported/default logging block, does not set an error or response entry, and falls through to the next item; final success still depends on common PlatformControl. This is not Type 111 support: the peer gets no Honda Type 111 response from stock.

## Prior-art comparison and model limits

Pinned MHI2 evidence uses a Type 111 request descriptor containing `streamConnectionID`, passes the original request to stock first, then clones the requested descriptor and adds `dataPort` and `streamID=111`. MHI2 also derives a separate receive context using its own target's session state. These are **PRIOR-ART VEHICLE PROVEN**, not Honda schema.

The ClarityLink negotiation model implements that MHI2-derived response profile. Its requirements for nonzero Type 111 `streamConnectionID`, cloned opaque fields, `dataPort`, and `streamID=111` are model assumptions for interoperability experiments, not Honda-confirmed fields. Its display/session model uses logical UUID strings; Honda's recovered `uuid` CF value is numeric. Do not equate those identities or serialize the synthetic model directly as Honda protocol data.

## Decision

```text
TYPE110 DISPLAY/STREAM CORRELATION: PARTIAL
DISPLAY DESCRIPTOR CONTAINER: ARRAY
MULTI-DISPLAY REPRESENTABLE: YES (container only; stock builder emits one)
STREAM DESCRIPTOR CONTAINER: ARRAY
MULTI-STREAM REPRESENTABLE: YES (container/mixed supported types; not Type 111)
DISPLAY UUID ↔ streamConnectionID: UNKNOWN
TYPE111 RESPONSE SHAPE: UNKNOWN for Honda
```

Sources: [Step 32 phone-facing `/info` path](../../step-reports/32-airplay-info-phone-path.md), [Honda descriptor](honda-copy-displays-info.md), [Honda Type 110 stream schema](honda-stream-entry-schema.md), [UUID flow](honda-display-uuid-flow.md), [display/stream analysis](display-stream-correlation.md), and [Step 38 mixed Setup](../../step-reports/38-type111-setup-security-contract.md).
