# 43t1 — R7C6 final R7C software closure

Status: `R7C_FRAMEWORK_RACE_BLOCKED`.

Preserved the preexisting R7C4/R7C5 local delta before edits in
`/tmp/claritylink-r7c6-start.patch`, with status in
`/tmp/claritylink-r7c6-start-status.txt` and untracked reports copied to
`/tmp/claritylink-r7c6-untracked-backup/`. Starting branch/HEAD were
`architecture/r7c-honda-target-adapters` / `0804bc0b3c6f6b7a63483562ce539eaa8550d778`.

Recovered the generic API17 x86 AVD path: the image-local optional device
catalog is missing, so the explicit `Nexus S` profile lookup fails. Generic
AVDs without `--device` run the pinned API17 revision 7 image. The hardened
runner passed its owned-AVD smoke and removed only its unique AVD/process.

R7C6 added one bounded generation/stream-bound diagnostic checkpoint
controller and JNI setup/cancel seams; the ARM production build does not link
the test controller. The recovered harness creates unique generic API17 x86
AVDs, verifies API/release/ABI/qemu/AVD name and sole target before install,
and cleans only its own process and AVD. Current APK SHA256:
`7049f72eff65576c723cb1a0288fdeea146af597130a37f8963f3a0bf06750f2`.

The captured 100-cycle phase used production native loopback sockets in all
100 cycles, fragmented Type110/Type111 LAB frames, H.264 decode, Surface post,
and per-cycle native counter/FD zero assertions. PSS ranged from 6,159–6,762
KiB after warmup through cycle 100 (6,240 KiB); native heap stabilized near
10.55 MB. The subsequent stress phase passed 25 Type111 Surface destroys,
25 Presentation dismissals, 25 Type111 peer-close isolation cases, setup and
decode aborts, Type110 Surface loss, and socket read/write shutdown. A focused
Activity-destroy run also passed with actual `onDestroy()`, active Type111
socket read, AudioTrack/input cleanup, and zero native owners.

Closure is withheld. After the cumulative stress sequence, the combined run
paused the Activity and released the primary Surface but did not reach
`onDestroy()` within the bounded wait; it was interrupted before a final
result. Focused Activity PASS evidence does not close this cumulative race.
The Dalvik production socket fault matrix also lacks explicit timeout,
refusal/collision, malformed/truncated/zero/oversized envelope, wrong
stream/generation, and Type111 fault-isolation cells. Fresh repo tests passed
(902 passed, 14 skipped), host socket and R7C1 ASan/UBSan and TSan passed, and
fresh NDK r23c ARMv7 build/import audit passed with zero unknown symbols
(artifact SHA256 `a53b18813024a44150e7eba1cfaba106f7d7a7e911602392ee63ff869fffd51d`).
Repo health and `git diff --check` pass locally.

No commit/push/merge was performed. PR #17 remains OPEN; its previously passing
Offline CI and CodeQL apply only to historical head `0804bc0...`. Exact-head
checks were not run. R7D remains CLOSED. No Honda or vehicle execution
occurred.
