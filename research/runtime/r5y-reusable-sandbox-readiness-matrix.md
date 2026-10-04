# R5Y — reusable sandbox readiness matrix

`READY` means ready **inside the host-only symbolic model**, never Honda/runtime ready. Each row is unit/failure tested directly or through the facade and fixture corpus.

| Component | Implemented? | Unit tested? | Failure tested? | Generation-safe? | Cleanup-safe? | Target-independent? | Reusable later? | Known gaps |
|---|---|---|---|---|---|---|---|---|
| Session model | READY | READY | READY | READY | READY | READY | READY | Real identity unknown |
| State machine | READY | READY | READY | READY | READY | READY | READY | Honda states unknown |
| Setup transaction | READY | READY | READY | READY | READY | READY | READY | Honda serializer/ownership unknown |
| Type110 preservation | READY | READY | READY | READY | READY | READY | READY | Runtime coexistence unknown |
| Secondary lifecycle | READY | READY | READY | READY | READY | READY | READY | Real lifecycle unknown |
| Generation ownership | READY | READY | READY | READY | READY | READY | READY | Real stable key unknown |
| Listener abstraction | READY | READY | READY | READY | READY | READY | READY | No socket or reachability |
| Security abstraction | READY | READY | READY | READY | READY | READY | READY | No crypto/authentication |
| Media abstraction | READY | READY | READY | READY | READY | READY | READY | Symbolic frames only |
| Decoder abstraction | READY | READY | READY | READY | READY | READY | READY | No real decode |
| Display abstraction | READY | READY | READY | READY | READY | READY | READY | No physical output |
| Cleanup | READY | READY | READY | READY | READY | READY | READY | Target close/finalizer unknown |
| Fault injection | READY | READY | READY | READY | READY | READY | READY | Named deterministic model points |
| Reconnect | READY | READY | READY | READY | READY | READY | READY | No phone/vehicle observation |
| Serializer | READY | READY | READY | READY | READY | READY | READY | Not wire format |
| Fixtures | READY | READY | READY | READY | READY | READY | READY | Invented values only |
| Tests | READY | READY | READY | READY | READY | READY | READY | Model coverage, not Honda soak |
| Static scope guard | READY | READY | READY | N/A | N/A | READY | READY | Static checks need review against dynamic bypass |
| Documentation | READY | N/A | N/A | N/A | N/A | READY | READY | Evidence must be updated later |
| Future adapter boundary | READY | READY | READY | READY | READY | READY | READY | No Honda adapter implemented |

The [evidence registry](r5y-honda-evidence-gap-registry.md) records all target gaps. A `READY` row cannot be cited as a deployment gate passing.
