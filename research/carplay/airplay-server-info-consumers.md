# AirPlay server-info consumer search — Step 31

> **Superseded by Step 32:** the consumer was recovered as `_requestProcessInfo` (`0x28a018`). The corrected phone-facing path and revised conclusions are in [Step 32](../../step-reports/32-airplay-info-phone-path.md). The remainder of this Step 31 record documents its search boundary and is not the current status.

**Scope:** offline static inspection of the identity-verified `jmcs` ELF and shared libraries from this acquisition. No vehicle, ADB, ptrace, or runtime hook activity.

## Symbol visibility and external consumers

`AirPlayCopyServerInfo` is `GLOBAL` (`g`) in the regular `.symtab` at ELF VA `0x282cd4`, with function size `0x8c4`. It is not present in `.dynsym` (`llvm-objdump -T` / `llvm-nm -D`). Consequently it is not available to ordinary dynamic-link imports from a separate mapped shared object. This materially lowers the external-library static-import hypothesis; it does not rule out a private runtime mechanism that passes an address by another route.

The runtime module inventory records 45 mapped shared libraries. Dynamic-symbol scans of the corresponding extracted shared objects found no imports/exports for `AirPlayCopyServerInfo`, `AirPlayReceiverSessionPlatformCopyProperty`, or `AirPlayReceiverSessionScreen_CopyDisplaysInfo`. The acquisition has hundreds of unrelated libraries; the relevant search set is the mapped process set, not every file in the image. No matching relocation/callsite was found in that set.

`jmcs` imports `dlopen` and `dlsym`, but the actual callsites inspected are in the generic dynamic-loader/SQLite symbol-loading support (`0x121aec` onward and `0x18d9ba`). No `AirPlayCopyServerInfo` lookup string is present. The printable `/info` string exists, but static string presence alone does not identify its handler or connect it to this builder. Therefore runtime lookup of this function is **not evidenced**, rather than disproven universally.

## Reverse response path

The known `_requestSendPlistResponse` callsite is in `_connectionHandleMessage` (`0x28a30c`) at `0x28afba`, and its object argument is the output of `AirPlayReceiverSessionSetup` from `0x28af72`. The response is serialized synchronously as binary plist (`CFPropertyListCreateData`, format `0xc8`) and sent by `HTTPConnectionSendResponse`; the connection state machine reaches `SocketWriteData` and `writev@plt`. This is a SETUP response path. No evidence shows that its object is built by, wrapped from, or otherwise contains the return value of `AirPlayCopyServerInfo`.

The reverse search therefore independently fails to connect server-info to the phone-facing response. Do not transfer the serializer/send proof from the SETUP object to server info.

## Current edge status

```text
CopyDisplaysInfo (0x287ae0)
 -> one main-display descriptor
 -> mutable one-element displays array from PlatformCopyProperty (0x28d328)
 -> inserted under "displays" by AirPlayCopyServerInfo (0x282cd4)
 -> returned mutable server-info dictionary
 -> UNKNOWN consumer / request handler / serializer / send
```

The local array and dictionary are mutable, so adding a second descriptor is structurally possible while the result is alive. A phone-facing mutation point is unknown. `DISPLAYS_PHONE_FACING=UNKNOWN`; `TWO_HOOKS_SUFFICIENT=UNKNOWN`; offline negotiation implementation and live connection test are not ready. The biggest blocker is one precise missing edge: the caller that consumes the returned `AirPlayCopyServerInfo` dictionary and submits it to a response serializer.

See [Step 31](../../step-reports/31-airplay-server-info-consumer.md), [Honda server info](honda-server-info.md), and [capability send path](honda-display-capability-send-path.md).
