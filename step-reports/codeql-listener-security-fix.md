# CodeQL listener security fix

Date: 2026-10-03

## Change

- Starting HEAD: `ba97b1896eeb415e31d37fce2dab7420958e6415`
- Ending HEAD: `adae40678b9a90bdd7397acb2c7ff938562b061f`
- Files changed: `src/claritylink-interposer/real_listener.py`, `tests/interposer/test_real_listener.py`, `research/carplay/type111-listener-runtime-contract.md`, `step-reports/43s1-executable-trampoline-listener-proof.md`, `docs/project/github-settings.md`, this report.
- CodeQL alert: `py/bind-socket-all-network-interfaces` at `real_listener.py:101`; fixed by policy validation before socket creation. GitHub alert #1 state is **fixed** on the pushed code revision; it was not dismissed.
- Real wildcard socket path: removed. `WILDCARD_TEST_ONLY` remains a policy enum only and raises `wildcard_bind_prohibited` before socket creation. Specific addresses are parsed as IPv4 and unspecified addresses are rejected; loopback test mode resolves only to `127.0.0.1`.
- Tests added: exact loopback bind, valid specific address, rejection of `0.0.0.0`, `::`, empty, and missing addresses before socket creation, and wildcard rejection before socket creation/bind.

## Verification

- Focused listener/contract/PREP2 tests: **47 passed**.
- `tools/run_tests.sh`: **659 passed, 3 skipped**, self-locator smoke passed, simulator JavaScript checks passed, diff check passed. Historical capture-backed scripts were skipped by the configured suite.
- `tools/check_repo_health.py`: **passed**, 0 broken curated links.
- Hosted Offline CI: **passed** on code commit `e5a8d59f37ef3516778144e6cb27b5910320d02a` ([run](https://github.com/bmreyes25/ClarityLink/actions/runs/37139779600)).
- Hosted CodeQL: **passed** on code commit `e5a8d59f37ef3516778144e6cb27b5910320d02a` ([run](https://github.com/bmreyes25/ClarityLink/actions/runs/37139779679)); alert #1 state **fixed**.
- Local CodeQL CLI/query pack: unavailable (`codeql` CLI is not installed); hosted CodeQL is the source of truth.

## Branch protection

GitHub CLI reported `ADMIN` permission. Applied and then verified branch protection for `main`: force pushes blocked, deletion blocked, no required status checks, no PR requirement, admin enforcement enabled. This preserves direct pushes. Exact manual review path: **Settings → Rules → Rulesets or Branches**, target `main`. Optional future stronger policy: require a PR, require the verified `Offline CI` and `CodeQL` checks, and require the branch up to date before merge.

Manual owner steps still open outside this task: enable secret scanning, push protection, and private vulnerability reporting; review allowed Actions and SHA pinning.
