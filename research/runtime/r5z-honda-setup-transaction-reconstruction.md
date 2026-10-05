# R5Z Honda Setup transaction reconstruction

`HONDA_STATIC` applies to the preserved stock Type110 path only. The custom Type111 branch is an `INFERENCE` design in the host receiver. This document gives function names rather than version-specific addresses.

```text
_connectionHandleMessage
  → parse incoming binary plist as CF dictionary                 HONDA_STATIC
  → AirPlayReceiverSessionSetup(session, request, &response)    HONDA_STATIC
      → read streams[] and each type                              HONDA_STATIC
      → Type110: read nonzero uint64 streamConnectionID           HONDA_STATIC
      → AirPlayReceiverSessionScreen_Setup                         HONDA_STATIC
      → derive Type110 screen key/IV and SetSecurityInfo          HONDA_STATIC
      → create listener; _AddResponseStream(type,dataPort)        HONDA_STATIC
      → Type111: unsupported branch, skip                         HONDA_STATIC
  → _requestSendPlistResponse(response)                          HONDA_STATIC
      → CFPropertyListCreateData → HTTPMessageSetBody             HONDA_STATIC
  → HTTPConnectionSendResponse → socket write                     HONDA_STATIC
```

The response dictionary is mutable until synchronous serialization, then the CF graph is released. Type110's response entry has `type` and `dataPort`; Honda Type111 response fields, screen allocation and child cleanup are **UNKNOWN**. Stock teardown handles known types 100/101/110. The finalizer closes stock session resources but is not a proved subscription point for custom children. The R5Z host transaction therefore allocates its own loopback listener first, builds a candidate response without mutating the primary snapshot, serializes it, and rolls back its child on failure. This tests architecture and does not establish an insertion seam in Honda.

The R5Z `SetupRequest` requires a nonzero uint64 ID for both screen types. Type110's requirement is `HONDA_STATIC`; Type111's requirement is `CURRENT_IOS_LAB_CONFIRMED` and external prior art, not Honda Type111 proof. `append_secondary` uses a copied Type111 request entry plus `streamID=111` and `dataPort` as an `EXTERNAL_PRIOR_ART` lab profile. The serializer is Python binary plist and does not reproduce Honda CF object ownership or HTTP behavior.

Evidence: [Honda request parsing](../carplay/honda-setup-request.md), [Step 27 send path](../../step-reports/27-honda-setup-send-path.md), [post-Setup boundary](../carplay/honda-post-setup-integration-contract.md), [Type111 response model](../carplay/type111-response-model.md).
