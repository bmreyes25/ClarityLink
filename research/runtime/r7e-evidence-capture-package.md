# R7E evidence capture package

R7E2 A0-R and A0-W fields are in [A0 evidence capture](r7e2-test-a0-evidence-capture.md). The R7E3 collector records these observations locally and adds command IDs, timestamps, exit statuses, full output, classifications, collector/plan IDs, repository HEAD, and redacted target identity. See the [R7E3 design](r7e3-a0r-collector-design.md) and [authorization packet](r7e3-a0r-authorization-packet.md). Keep target identity private/redacted; these are separate authorization scopes and neither authorizes Test A.

Use one sanitized record per separately authorized test. Store raw logs/captures locally under approved handling; commit only redacted summaries and hashes.

## R7E1 Test A fields

Record native artifact `claritylink-target-diag`, SHA-256 `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0`, build source `5b1d490`, expected identity `CLARITYLINK_DIAG_VERSION=1.0.0`, `API_TARGET=17`, `ABI=armeabi-v7a`. Expected self-test markers: `SELF_TEST_BEGIN`, `RESOURCE_COUNTS final=0`, `SELF_TEST_PASS`. Exact future command/path and expected invocation result remain unset until destination, privilege, power state, and rollback evidence are established. Expected execution in R7E1: NONE.

```text
test_id:
date_time_timezone:
software_commit_sha:
artifact_sha256:
vehicle_power_state: (record observed state; never infer)
exact_authorization_reference:
exact_approved_actions:
read_write_classification:
operator / stationary confirmation:
stdout_stderr_or_sanitized_log:
resource_counters_before_after:
display_id_type_dimensions_refresh_validity:
presentation_surface_states:
frame_count_and_timestamps:
observed_success_or_failure:
stop_condition_triggered:
rollback_actions:
process_listener_socket_decoder_surface_presentation_audio_input_absence:
temporary_file_absence:
center_ui_cluster_warning_audio_restoration_observation:
evidence_classification_and_scope:
```

Remove VIN, phone UDID, MFi credentials/material, private keys, auth blobs, and sensitive network identifiers. Human-visible notes/photos may support later geometry observations; OCR is not required. No evidence is collected during R7E because no vehicle test is authorized or performed.

## R7E4 research-backed refinement (offline only)

The prior manifest SHA-256 `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The normalized manifest at [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json) now carries plan version `R7E4-A0R-COMMAND-SET-1` and SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Its six added A0-R commands are fixed `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`; none executes those tools. Missing tool entries are recorded as `<TOOL>_UNAVAILABLE` and remain informational for A0-R; missing `rm`, `ps`, or `kill` also records a separate future-plan review blocker, while missing optional `md5` or unnecessary-by-default `chmod` does not block A0-R. `SELINUX_STATE_UNAVAILABLE` is informational and is never interpreted as disabled or permissive. `/data` `noexec` remains a hard blocker.

For future Test A, require host artifact mode `0755` before transfer, then verify the remote mode with `ls -l`; if the target executable bit is absent, stop without automatic `chmod`. SHA-256 remains the canonical identity; MD5 is optional transport consistency only. A0-W is proposed as one unique inert `0644` marker pushed through ADB sync, read-only inspected and optionally MD5-compared, then removed by exact path with a proven `rm`; it remains separately unauthorized and must not auto-run. See [R7E4 Android 4.2.2 research](r7e4-android42-target-path-research.md).


## R7E5A current evidence state

The A0-R run returned `A0R_PASS_FOR_REVIEW`; its sanitized summary is [r7e5-a0r-result.md](r7e5-a0r-result.md). Raw target identity and command evidence remain ignored, local, and unmodified. The A0-W evidence collector and exact command package are [r7e5a-a0w-authorization-packet.md](r7e5a-a0w-authorization-packet.md) and [r7e5a-a0w-plan-manifest.json](r7e5a-a0w-plan-manifest.json). A0-W evidence collection remains separately unauthorized; no A0-W evidence exists.
