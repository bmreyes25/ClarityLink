# R6E control transport

`LabSessionTransport` delegates only to an authority-owned channel with authenticated state and matching generation/session identity. It reads a structured `ControlRequest`, writes a `ControlResponse`, bounds timeouts to 30 seconds, and closes via the handoff. The authority adapter must frame and parse its actual RTSP/AirPlay transport; no undocumented wire format has been invented here.

All structured inbound values are bounded to 1 MB, 12 nesting levels, 4096 nodes, 256 entries per map/array, 4096 characters per string and 256 per key. Stale generation, malformed structures, disconnect and timeout fail closed. Unknown methods/paths are rejected by `ReceiverSession`; a failing request tears down receiver, authority and channel. Replay remains `SYNTHETIC`.

The Mac lab harness permits loopback binding only until a documented authority specifies a private interface. It opens no listener without the genuine authority. A future private-interface binding needs an exact interface identity, local reachability test, and network review; wildcard/public bind is prohibited.
