# AltScreen control plane and Honda status

Apple WWDC19 is high-level evidence that the vehicle selects instrument-cluster content and that multiple simultaneous video streams can serve main and cluster displays. It does not specify the private control messages. xcertplay/Harman evidence for display UUIDs, `altScreen`, 110/111, `suggestUI`/`showUI`, URLs, and per-stream setup is prior-art implementation evidence only.

Honda Step 28 establishes a local single-screen descriptor builder with `features` and `uuid` fields, but no caller, enclosing message, serializer, or phone-facing control-plane edge. No Honda `altScreen`, secondary role, second UUID, UI suggestion/selection, or view-area field is confirmed. The numeric UUID insertion is especially in need of data-type clarification. Thus the minimum known gating sequence is architectural, not a recovered Honda protocol transcript: advertise a distinct secondary display/capability; phone selects/proposes cluster UI; phone requests its stream with display correlation; receiver accepts/routes it; response supplies the independent stream port.

Control-plane direction, timing, schema, and correlation remain UNKNOWN for Honda. Do not implement guessed prior-art messages or fields.
