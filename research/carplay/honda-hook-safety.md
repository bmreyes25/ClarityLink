# Honda hook safety and Step 41 gate

Step 40B adds a strict Thumb-2 `BL` encoder/decoder, exact-build call-site patch descriptions, a 12-byte literal veneer encoding, mock reversible transactions, bounded INFO/Setup host semantics, and an optional Unicorn execution fixture. The two exact call sites were re-disassembled from the pinned `jmcs` ELF. Synthetic execution proves the branch → veneer → representative shim → stand-in callee → caller continuation, with tested register/stack preservation.

It still does **not** contain a process-memory writer, actual target executable allocation, page-protection manager, instruction-cache synchronizer, safe thread coordination, or live rollback. The mock transaction preflights all sites, verifies exact restoration in synthetic memory, and enters a loud critical state on restore failure. It does not establish hardware/live safety. Review [honda-executable-memory.md](honda-executable-memory.md) for the open platform requirements.

## Step 41 draft — parked no-op delegation only (not ready or executed here)

Run only after the real shim/allocation/patch/restore lifecycle has independent ABI, branch-range, permission/cache, concurrency, restoration, and review evidence. Step 40B does not clear this gate.

1. Confirm the running binary’s full identity and every selected call-site fingerprint.
2. Enable a single tightly scoped NOOP wrapper: record one bounded non-secret event, call the original exactly once, return its exact result. No capability edit, Type111 request/response, listener, or KDF.
3. Start normal CarPlay and verify stock center display behavior.
4. Verify the bounded event was recorded without request contents/secrets.
5. Disconnect CarPlay, restore original instructions, verify byte restoration, then confirm process health.

Abort on identity/fingerprint mismatch; unexpected bytes; inability to restore; missing original-call path; nonzero stock result when baseline succeeds; center CarPlay degradation; unexpected network/listener activity; or unbounded/missing diagnostics. If any abort occurs, disable project behavior and restore before any subsequent experiment. Type111 must remain disabled.

This draft is NOT a live-test authorization. Step 40B’s offline synthetic harness (emulated patch, delegation, restore, and byte verification) is **READY**; the process-level hook harness and Step 41 remain **NOT READY**. Type111 remains disabled.
