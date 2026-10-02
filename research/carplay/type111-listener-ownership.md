# 43S1 listener and generation ownership ledger

**Classification:** `LAB_HOST_RUNTIME_CONFIRMED`. All socket descriptors here are host test sockets; no Honda file descriptor or process was accessed.

## Ownership model

`GenerationListenerRegistry` maps an immutable generation key directly to a `PreparedListener`. Each listener owns its listening socket, at most one accepted socket, one cancellation event, and one joinable accept worker. A stale callback calls `close_generation(old_key)`; it never looks up and closes “the current listener.” The registry removes a generation mapping under its lock, then closes resources outside the registry lock.

| Generation | Listener | Accepted socket | Worker | Expected cleanup |
|---|---|---|---|---|
| B42 | L42 / ephemeral host port | A42 after connect | W42, exits after one accept | `close_generation(B42)` closes L42/A42 and confirms W42 joined |
| B43 | L43 / separate ephemeral host port | A43 after connect | W43, exits after one accept | remains open when stale B42 cleanup runs; later its own cleanup closes all three |

The concurrent-generation test connects clients to B42 and B43, closes B42 twice, and checks that B43's listener and accepted descriptor remain open and its worker remains independently owned. Explicit-generation ownership prevents stale B42 cleanup from reaching B43.

## Rollback evidence

- All listener preparation failure phases close a created real socket; worker/accept failure does not return an advertiseable listener.
- Immediate connect, never-connect timeout cancellation, client drop followed by generation teardown, real serializer failure, commit failure caused by generation supersession during the serializer boundary, explicit disable, parent teardown, and exact-generation replacement are exercised.
- Repeated create/close cycles check host `/dev/fd` counts and assert every tracked socket reports `fileno() == -1` and every worker is joined.
- Close is idempotent. Failure-injection tests check one listener close path, accepted socket closure, no orphan worker, and no stale-generation close of a replacement.
- The real-listener adapter is integrated with the 43R offline Type111 SETUP transaction. Listener is listening before the serializer callback, only `{type:111,dataPort}` is appended, Type110 response data is unchanged, and serializer failure rolls the generation back without a second serializer invocation.

## Limits

`/dev/fd` accounting and Python socket behavior are host evidence. This does not prove Android file-descriptor behavior under `jmcs`, Bionic socket timeout semantics, interface reachability, process shutdown callbacks, or cancellation of a hypothetical media worker. The reference listener worker accepts only; a later Type111 receiver/decoder requires a separate bounded worker and ownership review. Honda remains `HONDA_UNKNOWN` for all of these runtime behaviors.
