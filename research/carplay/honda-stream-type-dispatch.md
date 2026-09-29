# Honda stream type dispatch — Step 38

AirPlayReceiverSessionSetup (0x2854e0) iterates typed dictionaries from request streams[]. It reads type with CFDictionaryGetInt64 at 0x28590e: 100/101 dispatch to audio, 110 dispatches to screen setup, and unsupported values (including 111) log at 0x2861f6 then continue through the common increment at 0x286220.

The unsupported branch does not set Setup's status/error slot or mutate response/session state. Successful supported-entry responses already appended remain in the mutable response. Setup's final status comes from post-loop AirPlayReceiverSessionPlatformControl; if that and supported entries succeed, unsupported 111 does not fail the transaction. A supported-stream failure has a separate rollback path.

Recommended offline design: pass original request to stock; after stock success append a project-owned Type111 entry to an augmented response copy. The exact Type111 response schema and phone behavior remain unknown. See honda-mixed-stream-setup.md.
