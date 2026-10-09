# R7E3 A0-R operator runbook (preparation only)

This is a future-use guide, not execution authorization. Do not run the collector until a separate explicit A0-R authorization is granted and refers to the exact collector commit and plan manifest SHA-256.

## Before

1. Verify the approved collector commit and SHA-256 of `research/runtime/r7e3-a0r-plan-manifest.json` against the authorization packet. Any mismatch/change invalidates that authorization.
2. Park safely and keep the vehicle stationary. Directly observe the power state and record its exact displayed/control wording; do not infer or normalize it.
3. Confirm center display fully booted, cluster normal, and no unexpected warnings. Record the exact audio observation or enter `NOT_RELEVANT` when audio is not relevant.
4. Verify the operator has the separate A0-R authorization reference and can stop immediately.

## During

- Use the collector's exact reviewed invocation and enter every affirmative operator gate. The execution flag is not authorization.
- Do not improvise commands, retry, reconnect, scan, switch targets, invoke fallbacks, or troubleshoot ADB. If inventory is not exactly one intended target in `device` state, stop.
- After the reads, record the exact stock UI/cluster/warning/audio observation. The collector accepts `STOCK_STATE_UNCHANGED` only when those observations match the before state. Stop at any anomaly, unexpected UI/cluster/warning/audio change, timeout, privilege mismatch, platform mismatch, `noexec`, or command failure. Preserve partial local evidence. Do not issue a rollback command; A0-R has none.

## After

- Preserve the local evidence directory with its restrictive permissions; do not commit raw target identity or capture files.
- Confirm center UI, cluster, warnings, and relevant audio state remain unchanged. Record any deviation as a stop condition.
- Have the result reviewed before deciding anything further. Do not continue to A0-W or Test A. A0-W and Test A each require their own separate review and authorization.

## R7E4 research-backed refinement (offline only)

The prior manifest SHA-256 `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The normalized manifest at [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json) now carries plan version `R7E4-A0R-COMMAND-SET-1` and SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Its six added A0-R commands are fixed `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`; none executes those tools. Missing tool entries are recorded as `<TOOL>_UNAVAILABLE` and remain informational for A0-R; missing `rm`, `ps`, or `kill` also records a separate future-plan review blocker, while missing optional `md5` or unnecessary-by-default `chmod` does not block A0-R. `SELINUX_STATE_UNAVAILABLE` is informational and is never interpreted as disabled or permissive. `/data` `noexec` remains a hard blocker.

For future Test A, require host artifact mode `0755` before transfer, then verify the remote mode with `ls -l`; if the target executable bit is absent, stop without automatic `chmod`. SHA-256 remains the canonical identity; MD5 is optional transport consistency only. A0-W is proposed as one unique inert `0644` marker pushed through ADB sync, read-only inspected and optionally MD5-compared, then removed by exact path with a proven `rm`; it remains separately unauthorized and must not auto-run. See [R7E4 Android 4.2.2 research](r7e4-android42-target-path-research.md).
