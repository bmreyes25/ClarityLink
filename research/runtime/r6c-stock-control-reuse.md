# R6C stock controls reuse

`jmcs` defines `handle_carplay_iface_request_siri`, `handle_carplay_iface_request_ui`, `handle_carplay_change_modes`, iAP HID and `carplay_iface_*` callbacks. `CarPlayApService` exposes touch/main-window and UI status methods. These are connected evidence for in-process control routing and app-service coordination, but not a documented ClarityLink event feed. Steering button source and exact home/back/touch translation remain `UNKNOWN`; see [R6A strategy](r6a-audio-control-strategy.md).

The preferred future adapter keeps Honda's physical controls but needs a bounded event contract correlated with the authenticated CarPlay session. No event injection or vehicle control is implemented.
