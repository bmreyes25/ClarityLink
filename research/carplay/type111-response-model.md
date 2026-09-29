# Offline Type-111 response model — evidence-bounded

This is a protocol sketch, not an implementation or serialized payload.

```text
request entry:
  type: 111                    # prior-art convention; Honda currently rejects it
  remaining request fields: UNKNOWN

candidate response entry:
  type: 111                    # prior-art convention, not Honda-confirmed
  dataPort: CLARITYLINK_PORT_B # analogous to Honda Type-110 response; unproven for 111
  additional fields: UNKNOWN
```

Honda-confirmed template: a Type-110 SETUP request is dispatched to stock screen setup; the response entry contains type=110 and a dynamically allocated dataPort, then the Setup response object is sent through the binary-plist HTTP serializer. Honda does not currently accept type 111 through this dispatcher. Request/response identifier copying and display UUID binding are unknown.

This model is not ready for a complete interoperable offline handler: response parity, listener lifecycle/transport details, error semantics, phone correlation, and capability negotiation remain unresolved. It is a placeholder for a future fixture after the schema is proven.
