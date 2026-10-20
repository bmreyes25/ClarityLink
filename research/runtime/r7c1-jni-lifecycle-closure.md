# R7C1 JNI lifecycle closure

## Production contract

JNI now stores receiver and surface owners in `OpaqueHandleTable<T>`. Handles come from one process-lifetime monotonic positive ID allocator shared between both tables. IDs are never returned to the allocator, including after release; stale numeric IDs therefore cannot alias a later entry. A table lookup returns a `shared_ptr`, then releases the table mutex before receiver, surface, or Java work. Release removes the table entry first and then closes/invalidate outside the table lock. Receiver generation and surface stream are independently validated.

The JNI bridge makes no Java callbacks. It creates no global JNI references and retains no local reference past a JNI entrypoint. `ANativeWindow_fromSurface` returns a temporary native ref; the production window adapter acquires its own ref, and the temporary is released. C++ exceptions are caught at JNI entrypoints and translated to sanitized `IllegalStateException`s. A pre-existing pending Java exception is returned without being cleared or replaced.

## Host tests

`native/tests/opaque_handle_table_test.cpp` runs 2,000 concurrent registrations from eight threads, stale lookup after erase, retained `shared_ptr` behavior during erase, double/invalid release behavior, no ABA reuse, and positive-JNI-ID exhaustion. It uses the exact allocator/table template used by `jni_bridge.cpp`.

Environment: native host C++17. Result: PASS under normal, ASan/UBSan, and TSan builds. Evidence: `IMPLEMENTED_OFFLINE` for handle-table logic only.

## Still not exercised

This host has no Android JVM/JNI runtime. Direct calls into `Java_org_claritylink_android_NativeBridge_*`, Java exception propagation through a real VM, local/global reference semantics under ART, `AttachCurrentThread`/detach behavior, callback reentrancy, and native owner release against real framework `Surface` objects were not dynamically exercised. The bridge currently has no native-created worker threads, so thread attachment is not used. Those limits prevent the label “JNI lifecycle complete” and keep the R7D software entry gate closed.

## ECC findings

| Finding | Risk | Fix | Verification |
|---|---|---|---|
| A recycled counter or separate surface/receiver ID spaces could let a stale handle resolve to a later object. | Use-after-release/ABA. | One shared monotonic allocator; IDs never recycled; positive signed-JNI range enforced. | Concurrent 2,000-ID table test, erase/reinsert check, overflow test; API17 JNI build. |
| Calling receiver/sink code while holding the registry mutex could deadlock release against callback paths. | Deadlock/reentrancy. | Table operations return copied `shared_ptr`s and release the table lock before owner work. | TSan handle-table stress and source review. |
| A stale Java handle could be mistaken for a native pointer. | Arbitrary memory access. | Handles remain integer lookup keys; no pointer cast/exposure. | Source inspection and table API tests. |
| JNI exception state could be silently erased or native exceptions cross the ABI. | Lost errors/undefined ABI behavior. | Catch native exceptions; throw sanitized Java errors; preserve pending Java exceptions. | API17 cross-compile; real VM behavior remains untested. |
