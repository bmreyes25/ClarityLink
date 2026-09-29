# Type-111 SETUP response model — Step 33

Evidence-bounded protocol sketch only:

```text
candidate response stream:
  type: 111                  # prior-art convention; Honda does not accept 111
  dataPort: <allocated TCP port> # analogous to Honda Type 110, unproven for 111
  streamConnectionID: ?      # Honda Type 110 builder does not echo it
  display UUID: ?             # no Honda evidence it belongs in response
  other fields: UNKNOWN
```

Honda's Type-110 code derives per-screen AES key/IV from the request `streamConnectionID`, installs the crypto context, opens a TCP listener, then constructs a response entry with type 110 and the assigned `dataPort`. In the inspected response-building instructions, no identifier echo was seen. That is not proof that a Type-111 response must omit the identifier; Type 111 is not natively supported by this binary.

The outer Setup response is synchronously encoded as a binary plist and sent in the HTTP response. Exact Type-111 response fields, security requirements, port lifecycle, and whether the phone correlates entries by array order/type/ID are unknown.

**Readiness:** not a complete interoperable model. Only an analogous `{type, dataPort}` skeleton is supported, and the Type-111 port/crypto behavior remains receiver-specific and unproven.
