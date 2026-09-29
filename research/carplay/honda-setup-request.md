# Honda SETUP request parsing — Step 38

`_connectionHandleMessage` parses the request body as a property-list dictionary and calls `AirPlayReceiverSessionSetup` (`0x2854e0`) with receiver session in `r0`, request dictionary in `r1`, and response output slot in `r2` (`0x28af72`). Setup reads common root metadata then obtains typed `streams[]`; each dictionary's integer `type` is retrieved at `0x28590e`.

Supported routing is 100/101 audio and 110 screen. Values including 111 enter the unsupported log and continue to the common loop increment. This path does not mark an error. Assuming supported entry setup and final `AirPlayReceiverSessionPlatformControl` succeed, overall Setup returns success.

For Type 110, the descriptor must supply a nonzero `streamConnectionID` readable as uint64. The Type-110 branch derives/installs screen crypto and creates a listener. Honda does not read `streamConnectionID` for Type 111 because it has no Type-111 handler; requiring it for Type 111 is MHI2 prior-art only.

Known other fields read elsewhere include audio settings and client/root version metadata. No Honda Type-111 schema for timing, latency, screen identifier, crypto labels or format is proven. Preserve unknown descriptor fields rather than interpreting them.
