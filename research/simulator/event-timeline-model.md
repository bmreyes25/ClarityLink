# Digital twin event timeline

The Step 42D host twin records monotonically sequenced, in-memory semantic events. It stores no request payload, media bytes, key material, or proprietary capture.

Supported lifecycle events include:

- session_started
- type110_setup_preserved
- type111_requested
- type111_skipped_by_honda
- type111_listener_started
- type111_listener_failed (with injected stage only)
- type111_connected
- type111_config_received
- type111_frame_received
- type111_renderer_failed
- type111_teardown
- type110_still_active
- type110_disconnected
- full_session_teardown

The current twin records primary preservation as an explicit snapshot assertion in tests, not as a separate production event. Type111 event entries identify synthetic generation IDs and failure stage names only. Sequence number is a deterministic model ordering, not wall-clock time.

Tests use the timeline to prove stage order and cleanup explanation. No event implies Honda emitted an equivalent log or callback.
