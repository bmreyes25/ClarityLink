# R7C JNI contract

JNI entry points live in `native/platform/android/jni_bridge.cpp`; declarations are in `NativeBridge`. Java sees positive opaque IDs, never native addresses. Operations validate registry presence and generation. Surface IDs bind generation, stream type, and nonzero token. Receiver IDs own `ReceiverGeneration` through `shared_ptr`.

Attach converts Java `Surface` through `ANativeWindow_fromSurface`, takes a distinct native reference, then releases the conversion reference. Surface release removes its registry entry and invalidates/releases the window; a receiver's retained sink rejects later frames. Receiver release removes the ID and closes. Invalid or duplicate releases raise `IllegalStateException`; JNI does not silently clear exceptions. The registry lock is never held across receiver operations. Sink callbacks do not enter Java.

Current native worker threads do not call Java, so they need no JVM attachment. Any future callback must attach with `JavaVM`, use scoped local refs, release global refs at teardown, and avoid UI calls under receiver locks. Automated JVM tests for reentrancy, wrong generation/stream, Java exception propagation, and thread attachment have not run. ARM target compilation is pending.
