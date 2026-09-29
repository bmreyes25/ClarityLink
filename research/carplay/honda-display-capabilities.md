# Honda display capability path — Step 29

## Findings

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`) obtains `ScreenCopyMain()` once and returns a mutable dictionary with `edid`, `features`, `maxFPS`, physical/pixel dimensions, and `uuid`. Its direct caller is `AirPlayReceiverSessionPlatformCopyProperty` (`0x28d328`). When the requested property is literal `displays`, that caller invokes the builder once and appends its dictionary to a newly created CFArray, returning a one-element array.

This proves a local platform property container, but not a phone-facing message. `AirPlayCopyServerInfo` (`0x282cd4`) calls the platform property-copy routine three times while building a server-info dictionary; the exact argument/key corresponding to `displays`, and the further serializer/send chain, remain unproven. No second display descriptor is produced by this observed path.

| Question | Finding |
|---|---|
| Local container | One-element CFArray for property `displays` |
| Direct caller | `AirPlayReceiverSessionPlatformCopyProperty`, `0x28d328` |
| Potential parent | `AirPlayCopyServerInfo`, exact displays-key edge unknown |
| Phone-facing / serializer | Unknown |
| `features` meaning | Integer value derived through masks; bit meanings and actual value unknown |
| UUID | Main-screen property inserted using numeric setter; encoding/stability unknown |
| Secondary display | Not built in this branch; receiver-wide absence not established |

Do not infer that `features` means AltScreen or that this property is serialized to the iPhone. See `copy-displays-indirect-calls.md` and `honda-display-uuid-flow.md`.
