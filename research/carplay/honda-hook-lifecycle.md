# Honda hook lifecycle boundary — Step 40

Process start: the intended mode is OFF; no project behavior is active. Installing a hook and enabling ClarityLink behavior are separate concepts.

CarPlay setup: a future wrapper must call stock Setup with the original request and return the exact stock result when mode is OFF/NOOP/OBSERVE or a project augmentation fails. Project resources begin only after stock success and a valid project request.

Session start: future project state may become ACTIVE only after the original Honda session-start call succeeds. Honda stock Start remains delegated unchanged.

Session stop: future project teardown closes only ClarityLink-owned resources. A wrapper around Honda TearDown must not alter its args/result or call Honda cleanup for project-owned objects. Teardown must be idempotent.

Process exit: OS process cleanup is not a substitute for normal session teardown. Hook restoration and project cleanup should be attempted before process shutdown where the eventual host runtime allows it.

Static call order and APIs are recovered, but callback thread, reentrancy, and synchronization requirements are UNKNOWN. The Step 40 dispatcher stores no session singleton; its bounded diagnostics use a lock. No assumption of a single Honda callback thread is encoded.
