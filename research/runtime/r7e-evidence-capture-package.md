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
