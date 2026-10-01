# Honda receiver-session teardown lifecycle — Step 43H

**Evidence:** reference-hash-matched `jmcs` (`cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`), static ARM/Thumb disassembly. Full HTTP context: [HTTP failure lifecycle](honda-http-failure-session-cleanup.md). No Honda execution or live test.

`_connectionFinalize` (`0x289d90`) obtains per-connection private context from `[connection+8]`. A non-null session pointer at context `+0xf4` is passed to `AirPlayReceiverSessionTearDown` (`0x2852ec`) with null params; after return it is released and cleared. This relation is confirmed only for finalization when that pointer is present.

For null teardown params, Honda executes the full path: `AirPlayReceiverSessionPlatformControl` call first; session end logging and flag reset; `_ScreenTearDown`; `_TearDownStream` for each of two slots; `_ControlTearDown`; `_TimingFinalize`; `AirTunesClock_Finalize`; dispatch source cancel/release/clear. `_ScreenTearDown` sends command `0x71`, joins its worker if started, closes a nonnegative screen descriptor and sets it to `-1`, then clears its started byte. `_TearDownStream` signals/joins an active worker, closes nonnegative descriptors and sets them to `-1`, frees buffers, and clears state. No claim is made here about accepted ScreenStream socket ownership, crypto zeroization, or a single session-wide already-torn-down guard.

Some partial teardown requests use a non-null dictionary, iterate requested stream entries, and may defer Type110 teardown; this differs from the full null-params finalizer path. No supported project child callback is established. The platform-control callback is called at teardown entry, but the binary does not show a project child subscription API or prove that its callback contract is a universal teardown notification.

| Resource/event | Honda finding | Evidence class |
|---|---|---|
| HTTP control connection → receiver session | Finalizer's per-connection context has conditional session pointer `+0xf4`; non-null leads to TearDown then release/clear | HONDA_CONFIRMED |
| Type110 Screen worker/listener descriptor | Stop command, join, guarded close, fd reset | HONDA_CONFIRMED |
| Audio/control stream slots | Full teardown invokes worker/descriptor/buffer cleanup twice | HONDA_CONFIRMED |
| Session control/timing/clock/dispatch source | Ordered cleanup after streams | HONDA_CONFIRMED |
| HTTP fd equals ScreenStream fd | Distinct fields and teardown paths; equality/lifetime relation not shown | UNKNOWN |
| All session teardown comes from HTTP connection finalization | Not established | UNKNOWN |
| Session can be shared/reused across multiple HTTP connections | Not established | UNKNOWN |
