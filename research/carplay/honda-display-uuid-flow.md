# Honda display UUID flow — Step 29

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`) obtains the main-screen object via `ScreenCopyMain()` and reads the `uuid` property from that object. The function inserts the value under literal key `uuid` using `CFDictionarySetInt64`. This establishes a property-to-local-dictionary flow, and that the insertion is numeric at this call site. It does not establish the runtime value, UUID representation, stability, or whether the property is a session identifier versus a display identity.

No tracked caller or consumer is recovered. The returned dictionary has not been connected to a parent object, serializer, message, or socket. The Setup response evidence independently establishes stream entry `type=110` and dynamic `dataPort`; it does not read, emit, or correlate the display `uuid` in the evidence currently available.

| Question | Finding |
|---|---|
| UUID source | `ScreenCopyMain()` result's `uuid` property |
| Local representation | Integer setter (`CFDictionarySetInt64`); actual property type/value unconfirmed |
| Static or generated | Unknown |
| Session-scoped | Unknown |
| Emitted in another control message | Unknown |
| Present in SETUP request/response | Unknown from request; absent from the recovered stock response stream fields documented so far |
| Correlated with stream type/ID/port | Unknown |

Do not relabel this numeric property as a conventional string UUID without new type/runtime evidence. The exact next offline requirement is the matching ELF and caller/consumer xrefs; a later protocol capture would be a separate evidence step.
