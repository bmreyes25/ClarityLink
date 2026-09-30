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

Step 42F exports the selected mode's event list as JSON and displays it in the static visual demo. The page formats existing event names for readability; it does not invent lifecycle events. Evidence text comes from the replay records, and empty/strict and hypothetical timelines remain distinct.

## Step 42E canonical replay

The synthetic replay orders `session_started`, stock Setup start/preservation, capability gate, then either a strict-Honda skip or a hypothetical candidate setup/listener/connect/config/frame/render path. The hypothetical branch records Annex-B handoff, mock Display 1 submission, Type111-only teardown, `type110_still_active`, `audio_state_unchanged`, and finally synthetic full-session teardown. Events carry evidence labels where a wire/protocol interpretation could otherwise be mistaken for Honda behavior. Ports, IDs, timestamps, and frames are generated test values. The event stream is deterministic semantic output, not a Honda log format or timing trace.
# Step 42G decoder events

Hypothetical replay records `host_decode_not_run` with the backend availability and parser-fixture reason, followed by `synthetic_frame_source_fallback`. A future valid synthetic encode/decode path may add a successful decode event; the current timeline does not claim one. Decode failure or unavailability has no transition into Type110 or audio state.
