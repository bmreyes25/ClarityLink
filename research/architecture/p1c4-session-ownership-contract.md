# P1-C4 — session and resource ownership contract

This is a **conditional architecture gate**, not an existing Honda API. The [topology matrix](p1c4-receiver-topologies.json) gives resource ownership per candidate. The [offline model](../../src/carplay-session-model/receiver_ownership.py) rejects inconsistent symbolic claims; its success is `MODEL_ONLY` and cannot prove Apple/Honda acceptance.

| Function/resource | Mandatory owner in stock-preserving design A/D | ClarityLink role | Evidence gap |
|---|---|---|---|
| USB, iAP2 link, MFi authentication, primary AirPlay/control session | Honda `jmcs` | None; never claim stock FD, identity, master key or session pointer | No authorized external handoff. |
| `/info` displays and feature advertisement | Honda session owner | Can describe secondary capability **only through** a supported external extension | Stock builds one main display; no extension found. |
| Type111 SETUP and response entry | Honda session owner | Can supply a secondary endpoint only after an accepted, session-bound delegation | Stock skips 111; no response hook. |
| Type110 port, security, frames, audio/calls/Siri/controls | Honda and stock services | Observe no secret or mutable stock resource; no replacement | Isolation must be shown under all failure modes. |
| Type111 media endpoint/listener/accepted socket | Honda or ClarityLink under an explicit contract | May own a project listener and decoder; endpoint must be advertised by Honda and reached by iPhone | No endpoint delegation or peer/auth binding. |
| Type111 security | Honda session owner, with least-privilege per-stream authorization | May process frames only if a reviewed authorized security interface exists | Honda Type110 AES material cannot be assumed to work for 111; no key handoff. |
| Type111 rendering/Display 1 | ClarityLink after ingress and output admission | Can own H.264 decode and a bounded navigation surface | Android API17 and Display 1 admission are separate Phase 2 gates. |
| Secondary stop, primary disconnect, reconnect | Honda owns parent; ClarityLink owns only its allocated children | Generation-scoped, idempotent cleanup; secondary failure must leave Type110 running | No external start/stop or parent-death callback contract. |

## Required boundary proof

An eligible stock-preserving interface must document its actual entry and caller permissions, session-generation identity, `/info` timing, SETUP request/response ownership, per-stream authentication, exact media transport, stop/error/close callbacks, and independent Type110 failure behavior. A raw pointer, generic TCP listener, exported local symbol, mutable plist, or navigation status Binder fails these gates. Two sessions additionally need distinct legitimate accessory identity and Apple-supported simultaneous-session admission; shared wired transport needs an authorized iAP2 multiplex contract. A separate wireless transport needs its own lawful discovery and session lifecycle without displacing Honda. No such proof is present.

**Failure invariants:** never start a secondary child from stale generation or malformed SETUP; reject missing security/listener; acquire project resources transactionally; close only resources acquired; on secondary error keep stock primary live; on parent disconnect close all project children; never retry by claiming Honda resources. The tests exercise these invariants with synthetic labels, not protocol packets.

## Existing code and compatibility

Reuse [ReceiverSession](../../src/claritylink-jmcs/claritylink_jmcs/session.py) as a **full lab receiver** with its own lawful authority, [project lifecycle](../../src/carplay-session-model/project_lifecycle.py) for project-owned generation/cleanup, [transport](../../src/claritylink-transport/receiver_core.py), [native receiver](../../native/include/claritylink/receiver.hpp), and [Android sink](../../native/platform/android/android_surface_sink.hpp). These do not become stock callbacks by being callable. `AuthenticatedSessionHandoff` is intentionally single-use and nonserializable; it does not authorize copying Honda's session. Synthetic test authority and the earlier shared experimental PlayPort lab identity must not be treated as production credentials. This milestone installs no APK and changes no Honda configuration. A future no-APK consumer must prove its actual UID/service admission on Android 4.2.2/API17.
