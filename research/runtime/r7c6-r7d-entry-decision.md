# R7C6 / R7D entry decision

Decision: `R7C_FRAMEWORK_RACE_BLOCKED`.

The owned API17 AVD recovery and its identity/cleanup gate pass. A current APK
completed 100/100 socket-inclusive LAB cycles with per-cycle project-owned
counter and FD zero assertions, then passed Type110/Type111 setup/decode
cancellation, primary Surface loss, 25 Type111 Surface destroy iterations,
25 Type111 peer-close isolation iterations, 25 Presentation-dismiss
iterations, and native socket read/write shutdown probes. An Activity-destroy
case passes when run alone on the owned AVD. In the combined run, however, the
Activity paused and released its primary Surface but `onDestroy()` did not
arrive within the bounded wait; that run was stopped before a final result.

R7C remains unaccepted. The broad production native-socket matrix (timeout,
connection refusal/collision, malformed/truncated/oversized envelopes,
wrong stream/generation, and Type110 primary-failure scope) is incomplete.
The final combined emulator run did not reach a durable PASS. Host suite
(902 passed, 14 skipped), host ASan/UBSan, host TSan, fresh ARMv7 r23c build,
and API17 import audit pass. Exact-head hosted checks do not exist because no
commit or push was made. PR #17 remains unmerged; no R7D branch/worktree was
created. R7D entry remains CLOSED.

Next action: make Activity destruction deterministic after the cumulative
race stress sequence, complete the remaining production AndroidSocketAdapter
fault cells, then rerun one complete owned-AVD acceptance run and exact-head
verification before any merge decision.
