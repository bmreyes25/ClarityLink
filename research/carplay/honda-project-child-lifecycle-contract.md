# Hypothetical project child lifecycle contract — Step 43H

## Step 43I update (2026-10-01)

Honda evidence now proves a non-null application callback `_AirPlayHandleSessionFinalized` is installed in the receiver session delegate and called by the session CF runtime finalizer before platform/session resources are finalized. The 44-byte delegate is copied wholesale, so any future integration must preserve Honda's current callbacks and context. Honda also passes a request-aware `tearDownStreams` request through PlatformControl and distinguishes stream types 100, 101, and 110. It does not establish a Type111 child callback or supported way for a project child to subscribe to that request.

Updated attachment assessment: `SESSION FINALIZER: CANDIDATE`; `REQUEST-AWARE PROJECT STREAM ATTACHMENT: UNKNOWN`; overall two-signal model remains `NEEDS_MORE_STATIC_PROOF`. The synthetic exact-once contract below remains hypothetical and does not prove a supported Honda attachment point. See [Step 43I Honda lifecycle evidence](honda-session-delegate-lifecycle.md).

This is an offline design contract (`HYPOTHESIS` / `SYNTHETIC_TEST_VALUE`), not Honda behavior or Type111 implementation. Honda teardown evidence is summarized in [session teardown lifecycle](honda-session-teardown-lifecycle.md).

## State and ownership

Synthetic child state: `UNALLOCATED → ALLOCATED → ADVERTISED → LISTENING → CONNECTED → STOPPING → STOPPED`. Errors may transition any allocated state to `STOPPING`; one latched transition claims cleanup, and all repeated stop requests are no-ops after `STOPPED`.

| Resource | Owner | Exactly-once rule |
|---|---|---|
| Listener fd | Project child | Close only if allocated/open; atomically mark closed before close |
| Accepted socket | Project child | Same independent guard; never conflate with HTTP or Honda screen fd |
| Decoder/parser/buffers | Project child | Release once and clear ownership before invoking release |
| Optional response entry | CF response graph after proven successful insert; local reference released per stock pattern | Never independently release the Honda Type110 entry; rollback only the project entry/candidate graph |
| Parent receiver session | Honda | Project child may observe a verified parent lifecycle callback only; it never releases or tears down Honda session itself |
| Type110/audio/center-screen state | Honda | Project-only failures make no writes to these states |

Contract requirements: no cleanup before allocation; setup/insertion/serialization/commit failures release only project-owned resources; partial/retryable socket write keeps child alive; terminal connection failure is not treated as parent teardown until Honda's session teardown is observed; parent teardown dominates child lifetime; project cleanup is idempotent; Honda-owned Type110 is not independently released; no direct mutation of Type110 crypto, center-screen renderer, or audio. If Honda itself tears down the parent, Type110/audio changes are attributed to Honda's full teardown, not project cleanup.

`PROJECT_CHILD_ATTACHMENT_POINT: UNKNOWN`: the static binary shows TearDown and a platform-control callback, but no supported child subscription/notification interface spanning all parent teardown sources. This contract is implementable synthetically only until that attachment is proven.
