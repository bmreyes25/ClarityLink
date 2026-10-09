# R7E3 A0-R host test results

**Scope:** host-only synthetic fixtures. The collector was not run against Honda and no real `adb` executable was invoked by the tests.

| Case | Expected result |
|---|---|
| Default invocation | `NOT_AUTHORIZED`, nonzero, zero runner calls |
| Dry-run | exact redacted future sequence, zero discovery/ADB calls |
| One target | every target operation pinned with `-s` to the same fixture selector; local raw identity only; sanitized metadata redacts it |
| Zero, multiple, offline, unauthorized | stop after inventory; zero shell operations |
| UID 0/unexpected | stop after `id`; no later target operations |
| Wrong release/API/ABI | platform blocker before `pwd` or destination metadata |
| `ls -ld` unavailable | destination blocker; no `stat`, `busybox`, or `toybox` |
| `/data` noexec | noexec blocker; no readiness promotion |
| SELinux file unavailable | `SELINUX_STATE_UNAVAILABLE`; no `getenforce` |
| Timeout | record timeout; stop with no retry |
| Allowlist scan | manifest has no mutating operation, shell `-c`, or fallback in executable argument templates |
| Auto-chain check | A0-W remains evidence-required and Test A stays not authorized |

The pytest module is `tests/tools/test_r7e_a0r_collector.py`: **14 passed**. Canonical suite: **893 passed, 17 skipped**. Self-locator: **3 passed**. Simulator checks and Type111 failure twin passed. Repository health: **789 Markdown files, 154 indexed reports, 0 curated broken links, 0 forbidden extensions**. `git diff --check` passed. Exact-head Offline CI and CodeQL are recorded after the final push in the milestone report.
