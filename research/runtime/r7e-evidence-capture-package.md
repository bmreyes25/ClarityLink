# R7E evidence capture package

Use one sanitized record per separately authorized test. Store raw logs/captures locally under approved handling; commit only redacted summaries and hashes.

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
