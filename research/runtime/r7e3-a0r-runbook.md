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
