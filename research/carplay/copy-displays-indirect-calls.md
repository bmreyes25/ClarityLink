# `CopyDisplaysInfo` caller and capability path — Step 29

## Direct caller resolved

The matching ELF has one direct call site to `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (Thumb symbol `0x287ae1`, instruction VA/file offset `0x287ae0`):

- Caller: `AirPlayReceiverSessionPlatformCopyProperty` (`0x28d328`).
- Call: `0x28d370`.
- Property selector: literal `displays` (comparison at `0x28d33a–0x28d346`).
- Container: caller creates a mutable CFArray, invokes the builder once, appends the returned dictionary (`CFArrayAppendValue`, `0x28d382`), and returns that array through its output pointer (`0x28d666–0x28d66a`). Thus this property path returns a one-element array containing the main display dictionary.
- The generic property fallback at `0x28d654` invokes a different callback in the object at offset `+0x28`; it is not the display builder call. No stored function pointer/callback-table route to `CopyDisplaysInfo` was needed to explain this call.

The direct caller is a platform property-copy routine. An `AirPlayCopyServerInfo` builder (`0x282cd4`) calls this property-copy routine at `0x282e34`, `0x282f38`, and `0x283134` while building a server-info dictionary. The exact property argument and downstream registration/serialization/send path for the `displays` value have not been demonstrated. Do not yet label it a phone-facing message.

| Requested item | Finding |
|---|---|
| Function-pointer storage / callback table / slot | None required for this direct call; no indirect storage evidence ties to this function |
| Direct caller | `AirPlayReceiverSessionPlatformCopyProperty`, `0x28d328` |
| Initializer / interface type | Unresolved for the platform property object |
| Relevant parent | `AirPlayCopyServerInfo`, candidate container builder; exact displays-key edge unproven |
| Phone-facing message / serializer / socket | Unknown |

## Dataflow

```text
CopyDisplaysInfo (0x287ae0)
  -> one main-screen dictionary
  -> PlatformCopyProperty("displays")
  -> one-element CFArray
  -> possible AirPlayCopyServerInfo aggregation (not yet keyed to this property)
  -> serializer / transport: UNKNOWN
```

The full ELF is available in the ignored offline analysis copy recorded in `jmcs-acquisition-identity.md`; do not modify the immutable acquisition.
