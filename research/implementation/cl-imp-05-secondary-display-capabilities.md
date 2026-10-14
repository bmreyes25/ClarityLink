# CL-IMP-05 — Secondary-display capability model

**Status:** implemented for offline capability modeling. Honda production integration remains disabled. No Honda, vehicle, stock process, or live-iPhone operation was performed.

## Contract and ownership

`claritylink_jmcs.capabilities` now provides the internal typed contract for separate Type110 and Type111 display-stream descriptors. A plan is generation-scoped and validates stream type, unique connection identity, display role, owner, evidence class, and Honda status.

- The static ownership invariant is that factory Honda retains Type110 primary ownership; that invariant is separately marked Honda-confirmed. Each Type110 descriptor built for an offline plan has a synthetic connection ID/generation and therefore remains Honda-unknown. This does not attest to a particular Honda session. ClarityLink does not claim to own Honda's USB/iAP2, authentication, audio, microphone, Siri, call, or control paths.
- Type111 is an optional secondary navigation candidate owned by the ClarityLink secondary component in the synthetic model. Its topology and separate stream identity are supported by the 43P current-iOS lab observation; Honda acceptance and Type111 security remain unknown.
- The observed `maps:/car/instrumentcluster/map` navigation role retains current-iOS lab provenance and Honda-unknown status. The 43P capture did not establish a Honda URL requirement.
- Pixel geometry is an internal synthetic renderer constraint. The local fit helper preserves aspect ratio inside the configured safe rectangle. It does not parse or claim a CarPlay wire geometry field.

The sanitized 43R fixture is consumed by stream `type`, independent of array order. 43Q-A/Q-B ownership, duplicate-ID, teardown, and generation lifecycle contracts remain unchanged and are reused as the session-ownership evidence. The model creates no plist/wire serializer and does not add guessed fields to the Type111 request or response.

## Advertisement gates

`SecondaryDisplayCapability` now disables secondary advertisement by default. A two-display `/info` fixture requires the explicit `synthetic_lab()` profile; its geometry, UUIDs, feature values, and map URL are synthetic/lab values. The independent interposer profile also defaults disabled and rejects an enabled profile unless it is explicitly marked synthetic lab. A Type111 SETUP request is refused when that receiver session did not advertise the secondary capability.

The `InfoProfile` serializer and interposer remain ClarityLink lab models. No custom `/info` object is represented as a Honda profile or as evidence that a genuine iPhone accepted the synthetic fields. Existing receiver Type110 handling remains separate from the Type111 candidate.

## Evidence source map

| Source | Used for | Not inferred |
|---|---|---|
| 43P current-iOS PlayPort trace | Two streams, distinct IDs/ports, Type111 navigation-map role in that lab profile | Honda schema, geometry, security, or acceptance |
| 43Q-A | Independent Type110/Type111 synthetic screen identities and duplicate-ID rejection | Honda Type111 crypto |
| 43Q-B | Generation-scoped secondary child ownership and teardown/restart isolation | Honda callback timing or lifecycle |
| 43R | Type-based parsing, Type111-first ordering, stock Type110 response preservation, synthetic listener response contract | Honda acceptance of the appended Type111 response |

## Validation

Focused CL-IMP-05 tests validate Type110/Type111 identity and ownership-invariant provenance separately from synthetic session descriptors, production-disabled defaults, explicit lab admission, URL and geometry provenance, local safe-area fitting, duplicate UUID rejection, Type111 refusal when unadvertised, and mapping of the sanitized 43R fixture by stream type. Full offline and API17 suites are reported at the ECC gate.

## Remaining external requirements

Honda Type111 discovery and response acceptance, Apple descriptor field requirements, display UUID correlation, accepted map-role signaling, physical cluster geometry/safe area, production warning source/priority, primary-session delegation, and Type111 authentication/security remain unproven. Future compatibility work needs new lawful evidence and separate authorization. Synthetic negotiation is not genuine iPhone authentication.
