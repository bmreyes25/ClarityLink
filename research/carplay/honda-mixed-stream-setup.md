# Honda mixed-stream SETUP behavior — Step 38

**Target:** local `jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; static ARM/Thumb disassembly only.

## SETUP loop and unsupported Type 111

`AirPlayReceiverSessionSetup` (`0x2854e0`) reads `streams` as a typed CFArray, records its count, initializes index 0 and a zero status slot (`sp+0x60`), then iterates at `0x2858ee`. Each entry is fetched as a CFDictionary and `type` is loaded by `CFDictionaryGetInt64` at `0x28590e`.

- 100/101 enter audio setup.
- 110 enters screen setup at `0x28606e`; successful setup derives/installs per-screen crypto, opens its listener, builds and appends `{type:110,dataPort}`, and sets screen state.
- Other values below 100 or not equal to 110 route to the common unsupported log at `0x2861f6`.
- The unsupported block only loads logging state and calls `LogPrintF`. It does not store the Setup status slot, mutate the response streams, or change session state. It then falls through to the common index increment at `0x286220`, compares against the original array count, and continues.
- After the final element, Setup calls `AirPlayReceiverSessionPlatformControl` (`0x28cd88`) and stores its result as final status. On zero, it assigns the mutable response through the caller's output pointer at `0x286260`. The `_connectionHandleMessage` caller serializes only when this status is zero.

### Control-flow model

```text
create mutable response; status = 0
initialize common session/control state
read streams[] and count; i = 0
while i < count:
    entry = typed dictionary at streams[i]
    if prior status != 0: exit loop to rollback
    type = entry.type (CFDictionaryGetInt64)
    if type in {100,101}: run audio setup; error -> teardown/rollback
    elif type == 110: run screen setup; error -> teardown/rollback
    else: log unsupported type; do not set error or mutate response/state
    i += 1
run PlatformControl(...); final_status = result
if final_status == 0: *outResponse = mutable_response
else: rollback through Setup error path
return final_status
```

## Transaction finding

For a request containing `[100,110,111]`, `[111,100,110]`, `[110,111]`, `[111,110]`, or Type-111 alone, the Type-111 position itself does not alter the status or undo earlier work. Assuming every supported entry and the final platform-control call succeeds, overall Setup returns success. A successful Type-110 response appended before/after Type 111 remains in the same mutable response array. Type 111 itself contributes no stock response entry. This is a static control-flow conclusion, not a runtime phone acceptance test.

Other supported-entry ordering/duplication constraints remain independent: the type-100/101 stream slots are exclusive, and a second 110 may take an already-initialized/error path. Do not generalize “order never matters” beyond the unsupported Type-111 branch.

## Rollback distinction

Unsupported Type 111 causes **no rollback**. A real supported-stream/setup failure takes a different branch: it releases the local stream dictionary, invokes screen cleanup where applicable, records an error, and exits the loop. The error path calls `AirPlayReceiverSessionTearDown` with the original request and error before discarding the response; thus previously selected supported streams are eligible for teardown. This is whole-Setup failure handling, not a Type-111 rejection side effect.

Partial teardown is a separate recognized behavior. `AirPlayReceiverSessionTearDown` iterates the supplied `streams[]`: 100/101 call `_TearDownStream`, 110 calls `_ScreenTearDown` and its screen/session stop path, while unhandled type 111 does not receive Honda cleanup. A project-owned Type-111 listener/session must therefore have its own teardown owner.

## Delegation decision

**Use original request stock delegation** in the offline model: call stock once with the original descriptors, and only after stock returns success prepare the independent project stream and augment a copy of its response. Honda statically skips 111 without an error; filtering or intercepting the array would introduce unnecessary descriptor rewriting and ABI risk. If project setup or response augmentation fails, return the unmodified stock response and roll back project-owned resources. That is a fail-soft policy supported by the MHI2 implementation, but iPhone behavior when a requested Type-111 response is omitted remains unverified.

Honda's Type-111 response schema remains unknown. The offline response fixture uses MHI2's actual pattern: clone the requested descriptor, preserve all fields, set `dataPort`, set `streamID=111`, append. This is explicitly prior-art behavior, not Honda-confirmed wire schema.
