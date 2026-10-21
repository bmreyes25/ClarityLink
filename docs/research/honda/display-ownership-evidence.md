# Honda Display 1 ownership evidence

## Current bounded finding

Existing CL-R9C and CL-R10B public reports identify Honda-owned Android display/view paths and do not establish a supported arbitrary-frame or View admission API for a third-party client. They also leave the physical Navigation safe area, page-selection contract, warning precedence, frame freshness, owner-loss behavior, and restoration semantics unknown. Android display enumeration, `Presentation`, internal Binder reachability, or a private Xposed path alone does not grant frame admission.

| Contract field | Status | Required evidence |
|---|---|---|
| Authorized caller / admission | UNKNOWN | Versioned OEM contract, permission and ownership model. |
| Frame source, format and cadence | UNKNOWN | Supported frame contract with failure behavior. |
| Navigation viewport and transform | UNKNOWN | Physical geometry tied to correct page/trim/software version. |
| Page ownership and warning priority | UNKNOWN | Host-owned arbitration, warning precedence and non-mask guarantee. |
| Generation, withdrawal and stale-frame behavior | UNKNOWN | Revocation semantics and testable freshness contract. |
| Host crash/restart and factory restoration | UNKNOWN | Owner-loss behavior, cleanup and reversible restore procedure. |
| Vehicle-bus side effects | UNKNOWN | Explicit boundary review showing no unreviewed vehicle-control effect. |

No Display 1 adapter may attach until this contract is authorized, version matched, independently reviewed, and separately approved for any applicable target work. Keep production integration disabled.
