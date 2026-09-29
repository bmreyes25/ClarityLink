# Honda SETUP stream type parser — Step 38

Honda AirPlayReceiverSessionSetup reads streams[] as typed dictionaries and fetches integer key type at 0x28590e. Type 100/101 route to audio, type 110 to screen setup, and all other values including 111 enter the unsupported log block at 0x2861f6.

The unsupported block only logs. It does not set the local Setup status, remove response entries, mutate screen/audio state, or jump to rollback. It falls through to the common index increment/continue at 0x286220. After the loop, common AirPlayReceiverSessionPlatformControl runs; its return value controls whether Setup assigns the response and returns success. Thus 111 is non-fatal if other stream handlers and final PlatformControl succeed. It is not a supported handler and does not generate a stock response.

A separate nonzero error from a recognized stream invokes cleanup. Do not conflate those error paths with the no-error unsupported Type111 path. See honda-mixed-stream-setup.md for CFG and stream-order analysis.
