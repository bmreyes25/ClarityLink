# R7E4 A0-R research-hardened readiness decision

**Decision:** `R7E_A0R_RESEARCH_HARDENED_READY`. **A0-R execution:** not authorized, not executed. **First separately authorizable action:** A0-R only. **Next:** `READY_FOR_EXPLICIT_USER_A0R_AUTHORIZATION`.

The R7E4 A0-R plan incorporates documented Android 4.2.2 and legacy-ADB behavior. Its host-only collector with a default refusal, zero-call dry-run, fixed command allowlist, target pinning, operator gates, bounded timeout, local evidence capture, identity redaction, no fallback, and no automatic transition to A0-W or Test A. Synthetic test and repository-verification results are recorded in [test results](r7e3-a0r-test-results.md) and [R7E4 report](../../step-reports/43t1-r7e4-a0r-research-hardening.md).

**Collector source SHA-256:** `8693ac5d9165343bb94b9f56be4c4d0b8f3666884361e2f2d07f65a4b53a9c1d`. **Plan manifest SHA-256:** `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. **Exact collector commit:** `47605adad4e83faa8e05e028cd46282848546139`. These exact values are required by any later authorization; a source/manifest change invalidates the packet.

Repository verification: collector fixtures 17 passed; canonical suite 919 passed / 15 skipped; self-locator 3 passed; artifact SHA-256/mode gate passed; simulator checks passed; repository health passed (792 Markdown files, 155 indexed milestone/support reports, zero curated broken links); `git diff --check` passed. Exact-head Offline CI and CodeQL are recorded in the milestone report.

Exact implementation verification HEAD: `47605adad4e83faa8e05e028cd46282848546139`. Offline CI PASS; CodeQL PASS (all configured language scans). PR #19 remains OPEN and MERGEABLE.

Preserved decisions: `EXEC_PERMISSION_IS_TEST_A_MEASUREMENT`; `SPECIFIC_SAFE_POWER_STATE_SUFFICIENT`; A0-R Tier 1 `HONDA_READ_ONLY`; A0-W `BLOCKED_BY_A0_R_RESULT` and separate Tier 2 authorization only if later evidence shows it is needed; Test A `BLOCKED_BY_A0` / `NOT_AUTHORIZED`. `A0R_PASS_FOR_REVIEW` means evidence ready for human review only.

**A0-W NOT AUTHORIZED. TEST A NOT AUTHORIZED.** No Honda commands, writes, display activity, executable transfer, USB/iAP2, MFi, real iPhone, or live CarPlay action occurred.
