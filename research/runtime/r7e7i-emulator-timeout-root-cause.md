# R7E7I API17 timeout root-cause assessment

## Preserved event

Run `build/r7e7/runs/api17-runtime-cc036acc4cab.json` (SHA-256 `c168f5fe3c3e6069a38b2150d7b4c129320983a7886e4e701c2ac3a96a8e7982`) records 51 successful version/self-test pairs. Pair 52 version completed in 0.7554 seconds. Self-test output included `SELF_TEST_PASS`, then the host's unchanged 12-second subprocess deadline expired. The record does not show `SUPERVISOR_CHILD_REAPED` or guest trailer `__R7E6_STATUS:0`. Therefore success of the guest self-test is not proof of supervisor reap or guest exit; old run remains failed/inconclusive.

The record lacks SIGCHLD timing, child wait/reap duration, guest exit timing, per-command ADB latency, scheduler/CPU pressure, pipe ownership, memory growth and emulator state samples. It cannot select among guest scheduling, ADB latency, host contention, inherited output pipes or other causes. A later 100-pair pass and a 5-pair focused rehearsal are counterevidence to a deterministic failure, not a root cause.

This remediation also completed an isolated 3-pair x86 emulator rehearsal (`api17-runtime-42c56acd8e86.json`, SHA-256 `71b525f915357292a8af2bcbcf96c04babf7ad06c9e28dae5ff5b6eefc795bc7`). All 3 version/self-test pairs completed; maximum pair duration was 1.7287 seconds. Emulator and private ADB cleanup reported no failures. This short run exercises the updated runner path but does not resolve the historical root cause.

## Demonstrated defect and fix

The host runner called `communicate(timeout=12)` and, after timeout and process-group SIGKILL, called unbounded `communicate()` again. A descendant retaining stdout/stderr could keep that drain blocked. Cleanup now bounds drain and direct-child wait, closes capture pipes if descendants retain them, and reports this distinction. The 12-second test watchdog was not increased. No evidence establishes that this defect caused the historical event.

Python documents that `communicate(timeout=...)` does not kill the child and that descendant-held pipes may keep communication open; cleanup therefore must itself be bounded ([subprocess documentation](https://docs.python.org/3/library/subprocess.html)).

## Risk assessment

API17 evidence supports bounded rehearsal reliability, not resolution of the historical timeout. Test A remains blocked by Phase S evidence, process/relaunch safety, Phase C completion, exact path absence and the unresolved historical emulator event. No physical-device run was performed.
