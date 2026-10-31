# Type111 observation event records

This host-only event format preserves decoded receiver-boundary observations
with timestamps, phase labels, source methods, and source artifact hashes. All
checked-in examples are synthetic. The parser reads no device and does not
capture /info or SETUP traffic.

The machine schema is in
[type111-observation-events.schema.json](type111-observation-events.schema.json);
the reference parser is
[tools/honda-readonly-preflight/type111_observation_events.py](../../tools/honda-readonly-preflight/type111_observation_events.py).

## Evidence rules

- info_response records a complete decoded response and whether its complete
  display/capability fields advertise a secondary display.
- setup_request records the complete decoded stream type list. The absence of
  a Type111 request is meaningful only when a window_closed event marks the
  SETUP observation window complete.
- setup_response records accepted or rejected at the request/response
  boundary. Logs, process maps, socket tables, or packet presence alone do not
  establish this result.
- stream_created is distinct from setup_response; media availability needs
  its own complete media_observation.
- stream_closed and session_closed preserve teardown as separate lifecycle
  evidence.
- Every row points to an artifact SHA-256 and record identifier. Hash
  verification detects later byte changes but does not authenticate the
  collector, observation boundary, or interpretation.

The classifier distinguishes unobserved/incomplete evidence from a negative
result. It reports insufficient_observation when the required boundary or
window-completeness marker is missing. It does not infer decoded protocol
fields from logcat. A future on-vehicle observer requires its own reviewed
proposal and authorization; this format does not approve one.
