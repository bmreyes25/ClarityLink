# R6C factory substrate reuse matrix

`UNKNOWN` means no clean external contract is proven. Internal Honda ownership is not itself a `REUSE_API` result. Evidence links: [auth owner](r6c-honda-mfi-auth-owner.md), [iAP2](r6c-honda-iap2-owner.md), [control](r6c-honda-control-session-owner.md), [security](r6c-honda-screen-security-session-link.md), [services](r6c-carplay-service-boundary.md).

| Layer | Factory owner | Reusable? / form | ClarityLink responsibility / adapter | Unknown / confidence |
|---|---|---|---|---|
| USB | `jmcs` host code | `UNKNOWN` | `HondaIap2Transport` if seam found | fd/handoff; static probable |
| iAP2 | `jmcs` | `UNKNOWN` | same | transferable session; static confirmed owner |
| MFi auth | `jmcs` → factory I²C device | `UNKNOWN` | `HondaAuthenticationProvider` | external API; static confirmed internal path |
| pairing | `jmcs` iAP2/AirPlay | `UNKNOWN` | opaque context | exact transition; low |
| control-session crypto | `jmcs` AirPlay | `UNKNOWN` | `HondaCarPlaySessionTransport` | security-context export; low |
| `/info` transport | `jmcs` AirPlay | `UNKNOWN` | ClarityLink handler | request/response bridge; high internal owner |
| SETUP transport | `jmcs` AirPlay | `UNKNOWN` | ClarityLink handler | same |
| screen key derivation | `jmcs` session/screen | `UNKNOWN` | screen security provider | master-context transfer; high Type110 link |
| Type110 listener | `jmcs` | `REIMPLEMENT` if receiver moves | receiver Display0 | preserving stock ownership unresolved |
| Type111 listener | no accepted Honda path | `REIMPLEMENT` | receiver Display1 | current-iOS/Honda result unknown |
| audio | `jmcs` | `UNKNOWN` | audio router | same-session reuse; medium internal owner |
| touch | `jmcs`/app service | `UNKNOWN` | control router | event contract; low |
| steering controls | `jmcs`/vehicle interface | `UNKNOWN` | control router | source/translation; low |
| Siri | `jmcs` CarPlay interface | `UNKNOWN` | control/audio routers | exact routing; medium internal owner |
| Display0 | `jmcs` media | `REIMPLEMENT` if receiver moves | output adapter | Surface ownership; medium |
| Display1 | Honda Navigation/display services | `UNKNOWN` | admitted output adapter | admission and warning coexistence; medium |
| service lifecycle | `jmcs` launcher unknown | `UNKNOWN` | target lifecycle | launch/UID/recovery; low |

**Selected architecture: `ARCH_UNKNOWN`.** ARCH_A is the target, but neither A nor B has a demonstrated clean handoff. ARCH_E would overstate a scoped static search. Authentication-owner decision is `R6C_AUTH_INTERNAL_TO_JMCS`; target reuse result is `R6C_FACTORY_AUTH_REUSE_UNKNOWN`; transport result is `R6C_FACTORY_TRANSPORT_PARTIAL`.
