# R7C6 framework race results

Observed on Android 4.2.2/API17 Dalvik x86 using the owned emulator and current
diagnostic APK:

- Type111 setup cancellation after Type110 setup: rollback passed; Type110
  ownership remained.
- Type110 setup cancellation: no stream ownership remained.
- Type110 and Type111 decode cancellation before post: both cleanup scopes
  passed; the Type111 case preserved Type110 and accepted another Type110
  frame.
- Type111 `SurfaceView` removal during a decoded frame: actual
  `surfaceDestroyed` callback invalidated its native sink; after checkpoint
  release, Type111 failed locally and Type110 posted another frame.
- `Presentation.dismiss()` during the same Type111 pre-post window: callback
  invalidated the sink and Type110 continued.

Additional current-code evidence:

- Type110 Surface loss at the pre-post checkpoint caused session-global
  cleanup and released both stream owners.
- Type111 Surface destroy and Presentation dismissal each passed 25 iterations
  during the pre-post checkpoint; Type110 posted again after each teardown.
- Type111 peer-close isolation passed 25 iterations while Type110 remained
  active and accepted another frame.
- Type110/Type111 setup abort and decode abort each passed once.
- Native adapter read shutdown and write shutdown passed once.
- Activity finish with a Type111 native read, AudioTrack and input adapter
  active passed in an isolated focused run, including real `onDestroy()` and
  zero-owner checks. In the combined full run after the stress loops, the
  framework delivered pause and primary Surface destruction but did not
  deliver `onDestroy()` within the bounded wait. This cumulative ordering is
  still blocked; the focused pass does not substitute for the combined run.

The final combined run therefore has no complete acceptance result. Decision
remains `R7C_FRAMEWORK_RACE_BLOCKED` until the cumulative Activity lifecycle
case is reproducible and the combined suite records a durable PASS.
