# Type111 receiver-boundary event replay

The parser also accepts the verified, redacted Step 43P PlayPort laboratory
event stream through `type111_playport_source.py`. This source preserves the
original JSONL bytes and line offsets, checks a reviewed field/value allowlist,
and can pin ingestion to the canonical 43P SHA-256
`d57d08e17354d868a08712595d1a05526497534243930a492aa36131c7ab9913`. Its
findings are explicitly named `playport_*`: the trace reports PlayPort's
diagnostic events, not the Honda receiver's wire behavior. The 945-event source
observes two advertised display types (110 and 111), PlayPort's typed
`listener_ready` request/response summaries, connected sockets, VideoConfig,
first frames and server-shutdown teardown for both streams. Type110 and Type111
media were concurrently observed in this PlayPort/iPhone lab session. The event
source retains no raw plist, HTTP status/body, UUID, connection ID or media.
`listener_ready` is an application diagnostic event, not an independently
validated wire capture of the original Honda receiver's SETUP boundary.

`type111_playport_capture.py` ingests the source's JSONL output or SLF4J
SimpleLogger lines named `type111-oracle`. It filters other process log lines
in memory, validates each selected event with the allowlist parser, and writes
only event JSON plus a manifest to a new owner-only directory outside this
checkout (`0700` directory, `0600` files). The collector caps input at 32 MiB,
each log line at 64 KiB, event output at 4 MiB, and events at 2,000. It records
host ingest times separately from the receiver's `System.nanoTime()` values
and preserves original event order; the 43P stream contains concurrent-thread
timestamps that are not strictly ordered. It rejects duplicate event records
and stops at malformed or unreviewed data. An interrupted or failed ingest
keeps the valid prefix with `source_stream_complete=false`.

Example for a previously exported PlayPort logger stream (does not start the
receiver or contact a device):

```sh
python3 tools/honda-readonly-preflight/type111_playport_capture.py \
  --input /path/to/playport-log.txt \
  --output /private/path/new-capture \
  --receiver-commit f2679a26a593f544ba7822dfbac870544b4af92a \
  --phase 43p-canonical
```

The receiver commit is recorded as reported by the caller; it is not
cryptographically bound to event bytes. The manifest marks fields the current
source does not observe: RTSP response status, request/response correlation
IDs, and parent-session termination. Input EOF and a two-stream stop do not
make the protocol-observation window complete. The classifier refuses to
combine events if a trace contains zero or multiple session-setup markers,
because PlayPort's current event schema has no session ID.

The host-only decoder accepts an exported plaintext application-boundary JSONL
artifact, retains each raw plist body and decoded dictionary, and computes a
SHA-256 over the actual input bytes. Each parsed event carries an internal byte
offset/length into that source artifact. An expected digest from the private
manifest can be supplied at ingestion. The classifier accepts only a parsed
`Trace`, not caller-built event objects. Classification reparses the immutable
retained source bytes rather than trusting the event dictionaries cached on a
`Trace` instance.

The synthetic bench producer is
`src/claritylink-jmcs/claritylink_jmcs/synthetic_boundary.py`. It accepts only
`synthetic-*` session/phase identities, is attached only to
`ReplaySessionTransport`, and keeps its output in memory until a test or caller
explicitly asks for JSONL bytes. `ReceiverSession` uses it to record the
structured replay request and response at its `/info` and SETUP boundaries.
Its plist bodies are synthesized from the in-memory dictionaries, not copied
from a network wire. The end-to-end test exercises a Type110+Type111 synthetic
exchange and its parent-session teardown.

The session integration currently observes only `/info`, SETUP request and
response, and parent-session close. The recorder has explicit stream/media
record methods for synthetic fixtures, but `ReceiverSession` does not wire
those methods to stream creation or media callbacks. The observer is
best-effort: recording errors mark the observation incomplete and do not alter
the replayed receiver result. Callers must still treat any generated trace as
potentially sensitive: plist fields and base64 bodies are not redacted. Keep
trace bytes in private host-only storage and do not log or publish them.

The synthetic receiver-boundary source adapter is `tools/honda-readonly-preflight/type111_boundary_source.py`;
the correlated classifier is
[tools/honda-readonly-preflight/type111_observation_events.py](../../tools/honda-readonly-preflight/type111_observation_events.py).
The distinct PlayPort source adapter is
`tools/honda-readonly-preflight/type111_playport_source.py`.
The event schema is [type111-observation-events.schema.json](type111-observation-events.schema.json).
The checked-in fixture and bench producer are synthetic. Tests need no vehicle,
ADB, live iPhone, Honda binary execution, or privileged access. Archived Honda
binary analysis informed the candidate observation points documented below;
the archived binary is not executed or embedded by this prototype.

## What the trace can establish

- `/info` keeps the complete decoded dictionary, external HTTP status and
  original body bytes. The
  classifier reports only the number of `displays` descriptors; it does not
  infer undocumented descriptor semantics or turn one descriptor into a
  claim that secondary capability is absent.
- SETUP requests and responses retain exact decoded plist payloads, original
  body bytes, HTTP response status, phase, and matching request ID. A Type111
  accept is reported only for the same request with a complete 2xx response
  containing Type111 in the returned `streams`. A generic 4xx/5xx is reported
  as a SETUP error response, not a Type111 rejection; it may reflect
  authentication, routing, or another failure. A Type111-specific rejection
  remains unclassifiable until a receiver response code/body with known
  semantics is independently established. Redirects and 2xx responses without
  Type111 remain inconclusive. A Type111 request with no complete response is
  reported separately and is not called rejected.
- Stream creation, media availability, stream close, and session close are
  correlated by request ID and stream ID. Events from different phases cannot
  be joined. A complete setup-observation window is required for a negative
  request result. Type110 setup is reported only when a matching successful
  response also preserves Type110 in its response streams. The current session
  integration emits only parent-session close; stream/media lifecycle events
  require a separate synthetic event source.
- The computed digest detects later byte changes only when compared with a
  trusted, separately retained manifest. It does not authenticate the exporter,
  observation boundary, or its interpretation.

## Source boundary and limits

The synthetic adapter plus producer is a bench replay path; the PlayPort
adapter ingests an existing external iPhone/PlayPort bench trace. Neither is a
live Honda receiver hook, packet sniffer, or Honda-compatible event producer. A Honda trace
still requires an upstream exporter to have
observed decoded receiver boundaries and retained those plaintext records.
Request and stream IDs are supplied by that exporter; the adapter does not
independently bind them to a transport transaction or receiver-owned object.
The digest proves byte integrity, not event authenticity. It cannot decode
encrypted network traffic. The existing static analysis narrows
potential observation points to `/info` display-property construction
(`AirPlayReceiverSessionPlatformCopyProperty` and
`AirPlayReceiverSessionScreen_CopyDisplaysInfo`), inbound SETUP handling
(`_connectionHandleMessage` / `AirPlayReceiverSessionSetup`), response handoff
to `_requestSendPlistResponse`, and stream/session close callbacks (Steps 27,
31 and 43B). The phone-facing `/info` dispatch/serializer, externally visible
error status/body for rejected Type111, exact stream callback mapping, and any
low-impact runtime source remain unproven. Logcat markers, maps, socket tables, and packet presence do not
supply decoded fields. A runtime producer or instrumented observer requires a
separate reviewed proposal and explicit owner authorization.
