# Honda Setup response ownership

The observable phone-facing caller treats the response output as a caller-owned object:

1. `_connectionHandleMessage` passes an output slot (`&sp+0x54`) to `AirPlayReceiverSessionSetup`.
2. Setup publishes the mutable dictionary through the slot (`0x286260`) on successful completion.
3. The caller passes the value to `_requestSendPlistResponse`; that helper synchronously creates serialized `CFData`, copies its bytes into the HTTP message body, then releases the temporary `CFData` before returning.
4. `_connectionHandleMessage` then conditionally calls `CFRelease` on the response (`0x28b04e–0x28b054`).

**Contract in this recovered call path:** Setup transfers one owned (+1) response reference to the caller on success; caller owns cleanup. This is directly supported by the caller's release and the fact that Setup does not release the published response on its success path before returning. The Setup error path can release its local response and the caller branches on nonzero status without serializing it.

**Lifetime:** through synchronous property-list conversion and `HTTPMessageSetBody`; response object lifetime ends at caller `CFRelease` immediately afterward. The resulting body bytes are held by the HTTP message/connection independently. No evidence here establishes safety for asynchronous retention of the CF response, callback-time mutation, or cross-thread use. This is static ownership evidence, not a general API contract for all callers.
