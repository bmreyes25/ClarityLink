# Honda display UUID flow — Step 29

## Step 30 update

AirPlayCopyServerInfo (0x282cd4) requests the session property displays through AirPlayReceiverSessionPlatformCopyProperty and inserts its returned array into the mutable server-info dictionary. The display builder inserts uuid with a numeric CF setter. This still does not reveal a string UUID representation or any flow from that value into SETUP. The server-info serializer/send path and phone-facing status remain UNKNOWN. See honda-server-info.md and honda-display-capability-send-path.md.

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`) obtains the main-screen object through `ScreenCopyMain()` and reads its `uuid` property. It inserts that value under key `uuid` using `CFDictionarySetInt64`. The direct caller, `AirPlayReceiverSessionPlatformCopyProperty` (`0x28d328`), places the returned dictionary into the one-element array for property `displays`.

This establishes flow only as far as a local property array. `AirPlayCopyServerInfo` may aggregate platform properties, but the key/argument edge for `displays` and any serializer/send consumer are not proven. SETUP does not read this display UUID in the recovered request path, and its response stream entry contains type and dataPort without this UUID.

| Question | Finding |
|---|---|
| UUID source | Property on `ScreenCopyMain()` result |
| Local representation | Numeric CFDictionary setter; actual property type/value unknown |
| Static/generated or session-scoped | Unknown |
| Local container | `displays` property returns one-element CFArray |
| Phone-facing control message | Unknown |
| Present/correlated in SETUP | No UUID read/write found in analyzed Setup path |
