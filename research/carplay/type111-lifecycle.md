# Project-owned Type-111 lifecycle — Step 38

Honda owns its stock Type-110 session/listener. ClarityLink must own a separate Type-111 generation, listener, accepted socket, derived key/IV and CTR state, frame parser, codec config, and connection ID. No Type-110 internal pointer should be borrowed or overwritten.

## Desired lifecycle

```text
IDLE
  -> PREPARED (nonzero uint64 ID, independent crypto, listener bound)
  -> ADVERTISED (response append succeeded)
  -> ACTIVE (accepted phone socket)
  -> CLOSED (explicit Type111 teardown or whole-session teardown)
```

A changed connection ID or a new Setup generation replaces all project-owned transport state: listener and accepted socket, CTR position, partial frame, VideoConfig and H.264 parser state. Same-session UI/ViewArea changes are not transport resets absent evidence.

The offline lifecycle model in `src/claritylink-negotiation/lifecycle.py` contains only ID, port, generation and state. It has deterministic replace/rollback/teardown methods and no socket/key fields.

## Teardown evidence and open contract

Honda `AirPlayReceiverSessionTearDown` loops through entries and handles 100/101/110; unsupported 111 has no Honda cleanup. For Type 110 `_ScreenTearDown` signals/joins its worker, closes the listener descriptor, and clears its started flag. `AirPlayReceiverSessionTearDown` also dispatches the screen stop/cleanup path for type 110. Honda's partial teardown support is established for its own recognized entries; its API does not clean a project-owned Type-111 resource.

The MHI2 source explicitly distinguishes Type-111-only teardown from stock 110 and whole-session teardown. It clears Type-111 state on explicit 111 teardown and whole-session teardown, and filters 111 from the request passed to stock teardown when other entries remain. This is comparative behavior only.

Step 39 should hook/model the session lifecycle so project teardown runs exactly once for Type111-only or whole-session teardown, while 110-only teardown leaves Type111 alive only if the target protocol proves the same session remains valid. Honda's intended partial teardown semantics for unknown 111 are not evidence of how iPhone handles it.

## Step 39 host lifecycle implementation

Project state transitions: CREATED → SECURITY_READY → LISTENER_READY → RESPONSE_READY → COMMITTED. The committed response yields a PREPARED project generation; it becomes ACTIVE only after successful modeled stock SessionStart. Failed stock start and explicit project teardown close the fake listener, accepted test socket, secret buffers, and receiver reference.

Repeated teardown is safe. Honda Type110 is outside the project object graph. A new streamConnectionID requires tearing down the old generation and preparing fresh key/IV/listener/receiver state. This is a project-owned host lifecycle policy; Honda Type111-specific partial teardown remains unknown.
