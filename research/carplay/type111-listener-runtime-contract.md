# 43S1 real host listener contract (offline)

**Classification:** `LAB_HOST_RUNTIME_CONFIRMED` for the host socket implementation and tests. Honda interface policy is still `UNRESOLVED`; nothing here proves Honda Wi-Fi reachability.

## Implementation

`src/claritylink-interposer/real_listener.py` implements a real POSIX host IPv4 TCP listener. Setup is synchronous: create socket → mark non-inheritable (close-on-exec) → configure bounded accept timeout → bind port 0 → read assigned port → listen → start a joinable worker → wait for worker-ready signal. Only after `PreparedListener.create` returns may the SETUP contract read and append its assigned port. The integration test calls the stock serializer model after listener creation and connects immediately at that boundary; connection succeeds.

The worker handles accept away from the serializer thread, accepts at most one socket, uses a short timeout so cancellation is observed, and is never daemon/detached. `close` cancels, closes accepted and listening sockets idempotently, joins the worker, and reports a join timeout rather than claiming cleanup succeeded. Unexpected accept setup/accept errors are sanitized and invoke the captured exact-generation failure callback. Preparation-phase errors close any opened socket before propagating.

## Interface policy

- `LOOPBACK_TEST`: binds `127.0.0.1`.
- `SPECIFIC_ADDRESS`: binds only the explicit caller-provided local IPv4 address.
- `WILDCARD_TEST_ONLY`: rejected before socket creation; no wildcard test bind exists.
- Production `HONDA_INTERFACE_POLICY`: **UNRESOLVED**. No Mac policy is transferred to Honda.

Tests exercise loopback and valid specific-address policies; wildcard policy and unspecified addresses are rejection-only cases. No network client leaves the host. IPv6 is not enabled by this reference contract. A future Honda runtime observation must establish the phone-reachable address/family/interface and firewall/routing context before any listener can be approved there.

## Failure and expected behavior

Socket creation, options, bind, getsockname, listen, worker creation, and accept readiness are failure-injected. The 43R transaction integration proves listener preparation failure keeps the stock response unchanged and calls the serializer once. Serializer failure tears down the prepared generation and closes the real listener/worker; generation teardown after successful serialization closes it too. A phone that never connects remains cancellable and is closed on timeout/lease/teardown by its generation owner. This reference does not itself impose a lease duration; the caller owns that policy.

The worker does not decode or consume media. It stores the first accepted socket under the exact prepared generation. The accepted socket and listener remain owned until the lifecycle tears the generation down. Parent teardown behavior is exercised through the existing generation lifecycle, not Honda.

## Android/Bionic compatibility evidence

The preserved `jmcs` ELF dynamic symbol table contains undefined imports named `socket`, `bind`, `listen`, `getsockname`, `accept`, `close`, `fcntl`, `poll`, `select`, `pthread_create`, `pthread_join`, `pthread_mutex_lock`, and `pthread_mutex_unlock`. This is static evidence that the pinned binary's dynamic-link surface references these ordinary APIs (`HONDA_STATIC_COMPATIBILITY`); it does not prove a future adapter's linker namespace, Bionic `SO_RCVTIMEO` behavior, executable/thread policy, or use from the serializer callsite. The host Python implementation is not itself an Android implementation.
