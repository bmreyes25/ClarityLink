# R7C6 final 100-cycle runtime

On 2026-10-08 the current APK (`7049f72eff65576c723cb1a0288fdeea146af597130a37f8963f3a0bf06750f2`)
completed 100/100 API17 Dalvik cycles. Every cycle sent fragmented Type110
and Type111 LAB media through JNI and the production `AndroidSocketAdapter`
over AF_INET loopback, reconstructed each frame, decoded H.264, posted both
Surfaces, exercised AudioTrack/input/UsbManager/auth preflight, disconnected,
and asserted all eight project-native retained-owner counters plus the FD
baseline returned to zero.

Cycle-end PSS samples (KiB) were baseline 6,428; warmup 6,762; cycle 10 6,431;
20 6,500; 30 6,434; 40 6,488; 50 6,159; 60 6,211; 70 6,172; 80 6,208;
90 6,224; 100 6,240. Native heap allocation stabilized around 10,554,296
bytes. This run shows no clear monotonic growth; project counters remain the
ownership authority.

The cycle phase passed, but the subsequent combined framework-race suite
stalled waiting for Activity `onDestroy()` after `onPause` and primary Surface
release. The runner was interrupted before a final result line. Therefore the
socket-inclusive 100-cycle evidence closes that subgate only; it does not
constitute a complete R7C6 acceptance run. An isolated Activity-destroy run
on the same APK passed separately.
