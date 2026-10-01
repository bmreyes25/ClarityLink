# Honda platform lifecycle seam — Step 43J

Offline static trace against hash-matched `jmcs` (`cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`).

## PlatformControl routing

At `0x28cd88`, PlatformControl branches by command. `tearDownStreams` compares at `0x28cfe0`, fetches the request stream array, and iterates typed dictionaries at `0x28d02e–0x28d1b6`. Types 100 and 101 select separate platform state slots at `0x28d052–0x28d072`; 110 jumps to the platform update path at `0x28d1ae`; other values go through the unknown-type log at `0x28d0f8–0x28d126` and continue. Internal stream update/teardown follows. No load/call of the delegate control slot `session+0x24` occurs on this branch.

The callback-table fallback is reached only after recognized command comparisons miss. At `0x28d2c2–0x28d2d6`, Honda loads the callback at session `+0x24` and calls it, passing command, qualifier, params and output according to the platform call ABI. Therefore this callback can see other controls, but cannot see `tearDownStreams` or `setUpStreams` through this dispatcher. `TEARDOWNSTREAMS_TO_DELEGATE_CONTROL=NO`; `HONDA_APPLICATION_CONTROL_CAN_SEE_TEARDOWNSTREAMS=NO`; Type111 is unknown/ignored by the platform parser, not default-callback delivery.

## PlatformFinalize

`_Finalize` has one direct call to PlatformFinalize at `0x284d3e`, before later CF object cleanup. PlatformFinalize at `0x28cd60` checks `session+0x10`, returns safely when absent, and otherwise calls HID stop and `_TearDownStreams(session, NULL)`, frees the platform pointer, and clears the field. The only recovered caller is `_Finalize`; this gives one invocation per CF finalization call. No HTTP state or earlier stream notification is consulted.

## Symbol/call shape and limits

Both functions appear as global `.symtab` symbols and are absent from `.dynsym`. The observed callers use direct internal branches, not PLT indirection. This establishes neither a supported extension interface nor safe interposition. The application handler itself is not a Type111 route. Do not revisit it as the primary teardown attachment.

Classification: request-aware Honda platform event is proven; full-session safety signal is proven; platform extension mechanics and post-Setup project-child creation remain unproven. See [child lifecycle contract](honda-project-child-lifecycle-contract.md) and [Step 43J](../../step-reports/43j-platform-lifecycle-seam.md).
