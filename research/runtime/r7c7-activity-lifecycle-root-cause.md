# R7C7 Activity lifecycle root cause and closure

## Finding

The cumulative Activity failure was in the API 17 test harness lifecycle sequencing, not a production UI-thread wait. The test controller thread (`r7c2-integrated-test`) requests `finish()` through the main handler and waits for the Activity-destroy latch off the main looper. The main thread does not await a future callback. The trace shows main-looper heartbeat responsiveness before finish and after primary Surface loss, followed by `onPause`, Surface release, `onStop`, and `onDestroy`.

The first combined failure was caused by the Activity being the sole foreground component: ActivityManager reclaimed the otherwise empty test process before ordinary `onStop`/`onDestroy` delivery. A test-only `R7C7LifecycleGuardActivity` keeps the process non-empty while the Activity under test finishes. This makes the test exercise framework lifecycle delivery instead of process reclamation. A separate repeat-driver race was fixed by waiting for the guard to be resumed before launching each subsequent case.

A subsequent 25-repeat run found one diagnostic-only `IllegalStateException` from the test socket shutdown hook: normal reader completion had already unregistered all test sockets when `onDestroy` called the hook. The test hook is now idempotent when no diagnostic socket remains. The fresh 25-repeat runtime log contains 25 `ACTIVITY_DESTROY_DUAL_STREAM_RACE=PASS` events and no `SOCKET_CLOSE_ERROR`, `RESULT=FAIL`, or destroy timeout.

## Ownership and synchronization

`resetForNextCase()` clears checkpoints and synchronizes through the existing native checkpoint waiter; idle assertions bracket deterministic cases. Activity teardown releases Java-owned Presentation, surfaces, audio and input, shuts down active diagnostic sockets when present, disconnects native receiver state, and checks owner counters. Socket operations are tracked by stream so simultaneous Type110/Type111 adapters are independently closed. Lifecycle work remains on the main thread; test waits and network operations remain on controller/worker threads.

## Evidence

- Current 25-repeat log: `build/r7c2/runtime-5580-logcat.txt` (25 passes, zero socket-close diagnostic errors).
- Full combined log: `/tmp/claritylink-r7c7-combined-log.txt` (`RESULT=PASS`, lifecycle race pass after cumulative stress).
- Focused repeat driver output: `/tmp/claritylink-r7c7-activity-25-final-log.txt` (`RESULT=PASS ACTIVITY_DESTROY_REPEATS=25`).
- Platform: uniquely owned API 17, Android 4.2.2, x86, Dalvik emulator created and cleaned by the project harness.

**Decision:** Activity lifecycle blocker closed for the software emulator scope. No Honda, physical device, vehicle, real iPhone, or MFi interaction occurred.
