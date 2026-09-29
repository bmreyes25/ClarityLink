# Type-111 Setup failure atomicity — Step 38

## Transaction order

1. Call Honda Setup with the original request unchanged.
2. If Honda returns an error, do not create a project listener/session; return its status/response ownership unchanged.
3. If Honda succeeds and no Type111 exists, return the stock response unchanged.
4. Validate exactly one Type111 descriptor and its nonzero uint64 connection ID before allocating resources.
5. Prepare project-owned crypto/listener/session; if this fails, close any partial project resources and return the stock response unchanged.
6. Copy the response/streams container and append the cloned Type111 descriptor with project `dataPort` and the prior-art `streamID=111` field. If augmentation fails, immediately close project resources and return the stock response unchanged.
7. Transfer the augmented response to the existing synchronous serializer. If serialization/send fails, clean up project resources if the caller/session contract exposes that failure; otherwise retain state only until normal session teardown. This last cleanup integration is not proven by the two current candidate hooks.

## Why this preserves Honda state

Honda's unsupported-Type-111 branch has no status/state/response side effect. Supported 100/101/110 work proceeds normally and successful stock response entries remain in the same mutable response. Returning the original stock response on project-side failure leaves audio and Type110 entries and ports unchanged.

The fail-soft omission behavior after ClarityLink failure has MHI2 source precedent, but Honda/iPhone behavior when the request contains Type111 and the response omits it is unverified. Do not report it as a successful Type111 setup.

## Offline transaction model

`run_stock_first_setup` injects stock Setup, project preparation, and project rollback callbacks. It never opens sockets. Stock failure skips preparation. Project-setup and response-merge failures preserve a deep copy of the stock response and call project rollback. Tests cover the path without mutating stock input dictionaries.
