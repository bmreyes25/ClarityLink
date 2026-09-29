# Honda AirPlayCopyServerInfo — Step 30

## Step 31 consumer search update

`AirPlayCopyServerInfo` is GLOBAL in `.symtab`, but absent from `.dynsym`; it is not a normal dynamic export. Dynamic symbol scans of the 45 mapped shared libraries found no matching import/export or relocation. `jmcs` uses `dlopen`/`dlsym` for generic loader support, but no `AirPlayCopyServerInfo` runtime lookup literal or lookup call was evidenced. `/info` is present as a string, but has no recovered handler edge. Thus phone-facing consumption remains UNKNOWN. See [consumer search](airplay-server-info-consumers.md).

**Evidence:** authoritative local jmcs ELF, SHA-256 cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232. Offline static analysis only.

## Function and contract

AirPlayCopyServerInfo is at 0x282cd4 (size 0x8c4). DWARF identifies its declaration in AirPlayReceiverServer.c:156:

```c
CFLDictionaryRef AirPlayCopyServerInfo(
    AirPlayReceiverSessionRef inSession,
    CFLArrayRef inProperties,
    uint8_t *inMACAddr,
    OSStatus *outErr);
```

It returns a server-info dictionary (or null on failure); outErr is optional and receives the error status. The builder creates a mutable CF dictionary and populates it from server/session properties and local device/configuration values. It is not itself a serializer or network-send routine.

## Session property query and displays insertion

At 0x282e34, the function calls AirPlayReceiverSessionPlatformCopyProperty with inSession and the CF string key displays. If a value is returned, CFDictionarySetValue inserts that exact object into the result dictionary under the same key at 0x282e42; the temporary copied reference is released at 0x282e48 after insertion.

```text
AirPlayCopyServerInfo
  -> AirPlayReceiverSessionPlatformCopyProperty("displays")
  -> CFDictionarySetValue(serverInfo, "displays", returnedValue)
```

AirPlayReceiverSessionPlatformCopyProperty (0x28d328) compares the key at 0x28d332–0x28d342. Its displays branch creates a mutable CFArray, calls AirPlayReceiverSessionScreen_CopyDisplaysInfo (0x287ae0), appends the returned main-display dictionary, and returns the array. Thus the builder inserts the one-element array returned by that branch.

## Callers and transport status

DWARF and the public function symbol are present. No direct call to AirPlayCopyServerInfo was recovered in the available complete disassembly; no indirect callback-table or relocation consumer has been proven. The function contains no HTTP response serializer or socket send. The available _connectionHandleMessage → _requestSendPlistResponse proof is specifically for AirPlayReceiverSessionSetup's output object, not this server-info dictionary.

Therefore the triggering request/URI, request phase, network-facing caller, server-info serialization format, and send function remain UNKNOWN. Do not reuse the proven SETUP binary-plist send path as evidence for server-info.

## Ownership and mutation

The builder creates a mutable server-info dictionary. The displays array is created with CFArrayCreateMutable. The main descriptor dictionary is mutable as well. The callback returns a copied/owned value; AirPlayCopyServerInfo inserts it into the mutable result dictionary, then releases its temporary ownership. This proves local structural mutability while the returned dictionary is alive. It does not prove the server-info value reaches a phone or identify a safe phone-facing mutation hook.

| Decision | Result |
|---|---|
| Server-info return type | CFLDictionaryRef |
| Displays query | Confirmed, property key displays |
| Displays insertion | Confirmed in returned dictionary |
| Server-info dictionary mutable during construction | Yes |
| Displays container mutable | Yes, CFMutableArray |
| Phone-facing server-info path | Unknown |
| Safe capability mutation point | Unknown |

See honda-display-capability-send-path.md, honda-display-capabilities.md, and Step 30.
