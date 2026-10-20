# R6D factory auth/session object ownership

All findings refer to the preserved build, not a running Honda. `jmcs` is the process owner unless stated otherwise. Thread affinity is recorded only where a thread or loop is visible.

| Object | Creator / consumer / close | Form and transfer finding | Confidence |
|---|---|---|---|
| USB device/fd | USB host/udev path → iAP; exact open/close untraced | internal device; no fd passing evidenced | HONDA_STATIC_PROBABLE |
| iAP2 device and owner context | `ios_iap2`/`jiap2_get_dev` → `auth_result` and `do_attach`; detach symbols exist | in-process pointer; owner-context flag written at `ios_iap2_set_authenticated+0x44`; no external handle | HONDA_STATIC_CONFIRMED for local pointer/flag, UNKNOWN teardown |
| Factory auth provider and I²C fd | `os_auth_cp_obtain` opens configured auth channel, `os_auth_cp_release` closes; `uwh_ipod_cp_*` consumes | process-local fd/mutex; no transfer contract; hardware not accessed in R6D | HONDA_STATIC_CONFIRMED |
| CarPlay attach/device | `do_attach` adds/probes generic device; `mc_ios_dev_attach` calls `mc_carplay_attached`; `mc_carplay_detached` cleans audio/screen/HID | pointer/context via internal callbacks; no externally stable session ID | HONDA_STATIC_CONFIRMED for direct calls; indirect dispatch UNKNOWN |
| AirPlay receiver server | `_AirPlayThread` creates, sets delegate, runs CF loop, releases on exit | process-local CF object and thread | HONDA_STATIC_CONFIRMED |
| AirPlay receiver session | internal connection handler calls `AirPlayReceiverSessionCreate`; CF instance retains server and screen; `_Finalize` releases session resources | process-local CF object; delegate is not external IPC | HONDA_STATIC_CONFIRMED |
| Control connection | AirTunes connection handler reads messages and sends plist responses; `_connectionInitialize` sets socket keepalive | internal socket/connection; no `SCM_RIGHTS` handoff or raw request service found | HONDA_STATIC_CONFIRMED internal, transfer unsupported by found boundary |
| Pairing/SAP context | `APSMFiSAP_Create/Exchange` at connection `+0xc4`, `Delete` at teardown; decrypts session security fields | connection-owned opaque state; no export established | HONDA_STATIC_CONFIRMED |
| AirPlay master screen material | `AirPlayReceiverSessionSetSecurityInfo` installs 16-byte master material in session after control exchange; finalizer clears associated crypto | session-private; Type110 KDF consumes it; no external reference API | HONDA_STATIC_CONFIRMED |
| Type110 screen object | session creates screen; Setup installs derived AES-CTR; finalizer tears down | process-local screen/listener, not transferable | HONDA_STATIC_CONFIRMED |
| Audio session | `jmcs` CarPlay audio callbacks and Android media | internal routing; independent handoff unproven | HONDA_STATIC_PROBABLE |
| Control/HID session | `jmcs` iAP/HID and CarPlay callback code | internal event ownership; external handoff unproven | HONDA_STATIC_PROBABLE |

The observed reference graph is `iAP device → owner context/attach → CarPlay device callbacks` beside `_AirPlayThread → server → connection → AirPlayReceiverSession → screen`. The link associating a particular authenticated iAP2 device to a particular AirPlay connection is not a recovered transferable object. No object above can be treated as an R6B `SessionHandoff` merely because it is a pointer, fd, or CF instance.
