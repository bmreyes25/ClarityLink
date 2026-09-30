# Step 42B — network/control-plane proxy feasibility

## What the current evidence proves

- Honda `/info` is served by jmcs code: `_requestProcessInfo` calls `AirPlayCopyServerInfo`, receives the dictionary with `displays[]`, and passes it to the synchronous binary-plist/HTTP response path (Step 32 static dataflow).
- Honda Setup parses the phone-facing property-list request in jmcs. `AirPlayReceiverSessionSetup` receives the session and request, then the caller serializes its response dictionary into an HTTP 200 binary-plist body and writes through the connection state machine.
- Type 110's Setup path opens an ephemeral listener (`bind` to port 0, then `getsockname`) and returns its assigned `dataPort`.
- Honda currently skips Type 111 and adds no Type 111 response; stock Type 110 remains eligible to succeed.
- A prior live process snapshot observed two jmcs-owned established IPv6 flows to one peer, but neither was classified as `/info`, Setup, Type110, or audio. The disconnected snapshot's port 5000 listener was not attributed to ScreenSession or a control API. Do not treat it as the CarPlay proxy endpoint.
- No init configuration, service Binder, or native component establishes a supported network proxy or control socket.

## What a proxy would have to do

1. Become the phone-facing endpoint for the relevant `/info` and Setup transactions without breaking jmcs's current session and Type110 flow.
2. Preserve/forward the Setup request and stock Type110 response correctly.
3. Advertise the second display and add a Type111 response entry with a listener reachable by the iPhone.
4. Obtain or derive whatever session/security inputs the iPhone expects for the secondary stream.
5. Own Type111 data socket, framing/decryption, lifecycle and teardown.
6. Deliver decoded frames to an ExternalDisplay renderer host that currently has no supported frame IPC.

None of the reviewed Honda interfaces provides traffic redirection, Setup response interception, a Type111 listener handoff, or session master/key transfer. A transparent proxy can only observe/write the needed bytes if it is actually in the route. An application-level proxy would also need the real transaction framing and authentication behavior, not merely the serializer's internal binary plist.

## Feasibility matrix

| Question | Result | Reason |
|---|---|---|
| Can it preserve Type110 in principle? | **UNKNOWN** | Additive response rewriting could preserve the stock entry, but no actual in-path proxy or phone acceptance is proven. |
| Can it intercept `/info` and Setup today? | **UNKNOWN / no seam found** | Two process-owned live TCP flows were not classified; port 5000 is not identified as the CarPlay control endpoint. No system proxy/configuration hook is known. |
| Does it need keys? | **UNKNOWN for Honda Type111** | MHI2 reuses session master-derived screen security; if Honda expects equivalent encrypted stream content, a secondary receiver needs compatible security inputs. No external transfer API exists. |
| Can it create Type111 response? | **Technically modelable, Honda acceptance UNKNOWN** | It could construct a plist response only after a valid request and listener exist; field schema and phone behavior remain unproven. |
| Can it own dataPort? | **Technically modelable, path UNKNOWN** | It can bind a local port in software, but iPhone reachability, interface selection, response semantics and conflict-free routing are not shown. |
| Does current proxy feasibility beat jmcs? | **No** | It adds unknown network route, authenticated state, response rewrite, and host-frame transfer boundaries. |

## Decision

```text
NETWORK_PROXY_FEASIBLE: UNKNOWN
PROXY_MUST_HAVE_KEYS: UNKNOWN for Honda; YES if it must decrypt a stream using reused session-derived material
PROXY_CAN_DELEGATE_TYPE110: UNKNOWN (architecturally possible if transparently in-path)
PROXY_CAN_CREATE_TYPE111_RESPONSE: UNKNOWN for Honda/iPhone compatibility
BEST CONTROL-PLANE FIT: JMCS, because it already owns Setup, session and Type110 KDF inputs
```

Do not attempt traffic redirection or attach to port 5000 as part of this milestone. A proxy should be reconsidered only after a documented, supported route exists and session-material requirements are known.
