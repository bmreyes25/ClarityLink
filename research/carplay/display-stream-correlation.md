# Honda display-to-stream correlation — Step 34

**Evidence scope:** identity-verified `jmcs` ELF, offline static analysis. SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. No vehicle, ADB, ptrace, firmware patch, live hook, or Type-111 implementation.

Step 32 proves `/info` returns the exact server-info object containing `displays[]` to the phone-facing binary-plist response path. Step 33 establishes that the stock Type-110 setup reads a per-stream `streamConnectionID` and uses it in screen-stream security setup. It does **not** establish a relation between that ID and the display descriptor's `uuid`.

## Evidence-bounded model

```text
GET /info
  -> serverInfo["displays"][0] = main screen descriptor
       uuid comes from a numeric property on ScreenCopyMain()

SETUP streams[i]
  -> type = 110
  -> streamConnectionID: uint64_t
  -> AirPlay_DeriveAESKeySHA512ForScreen(masterKey, 16, ID, key, IV)
  -> AirPlayReceiverSessionScreen_SetSecurityInfo(key, IV)
  -> ServerSocketOpen(..., port 0, ...)
  -> response stream { type: 110, dataPort: assigned port }
```

The SETUP stream path contains no demonstrated read of display `uuid`; the `/info` display builder contains no demonstrated `streamConnectionID`. No structure with both values has been identified. Therefore an advertised second descriptor is not yet proven sufficient to cause a Type-111 request or to bind that request to the descriptor.

| Candidate relation | Honda result |
|---|---|
| Request stream -> 64-bit streamConnectionID | Confirmed in inlined `_ScreenSetup` within `AirPlayReceiverSessionSetup` |
| streamConnectionID -> screen crypto | Confirmed; used in screen key/IV derivation |
| streamConnectionID -> listener/response | Same Type-110 branch creates the listener and response entry; explicit echo/copy-through not observed |
| display UUID -> SETUP stream | No link found in analyzed paths |
| display UUID -> crypto/session identity | No link found |
| Type 111 -> cluster display | Honda rejects type 111 at invalid-type branch `0x2861f6` |

## Decision

`DISPLAY_TO_STREAM_BINDING = UNKNOWN`. The ID's proven role is per-screen cryptographic derivation, not display selection. A candidate future model may carry a distinct Type-111 `streamConnectionID` for a separate stream/security context, but this remains a hypothesis from other receivers, not a Honda-confirmed request/response schema. A second `/info` descriptor by itself is **not proven sufficient**.

Prior-art repositories describe Type-111 streams and control/UI state, but their receiver-specific behavior cannot fill the missing Honda edge. Their current-source evidence is summarized separately in `prior-art-altscreen.md`; no version-history conclusion about when feature tokens became required is asserted here.

## Reclassification

The display UUID is best classified as **PRESENTATION/CAPABILITY IDENTITY** in current evidence, with a possible additional role in input/display association not explored here. It is not demonstrated as a transport binding or a cryptographic input. A dedicated data listener and its assigned port provide a natural media-transport association for the accepted socket, while the display descriptor tells the phone about a display/presentation target. The wire protocol may correlate those independently; Honda's phone-side relation is not recovered.

`LISTENER_IS_STREAM_BINDING=YES` at the network endpoint level (a TCP peer connecting to listener B is connected to listener B's socket generation). Persistent linkage from Honda's Setup object fields to `_ScreenThread` ownership remains partial. The listener association answers how the socket can be assigned to a transport without UUID; it does not answer how the phone chose that Type-111 stream.
