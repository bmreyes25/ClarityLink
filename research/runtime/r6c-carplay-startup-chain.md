# R6C factory startup chain

| Edge | Owner / object | Evidence and confidence | Thread/lifetime |
|---|---|---|---|
| Physical USB attach → USB host transport | `jmcs` `libudev` and `jiap_usb_host_mode_transport_*` | Symbols and dependency: `HONDA_STATIC_PROBABLE`; exact attach callback/fd `UNKNOWN` | `UNKNOWN` |
| USB transport → iAP2 physical device | `jmcs` `ios_iap2_*`, `iap2_core_attach` | Co-resident symbols and `mc_iap2_attach`: `HONDA_STATIC_PROBABLE`; exact handle edge untraced | device-scoped, inferred |
| iAP2 → factory accessory authentication | `iap2_acc_auth_*`, `acc_auth_*`, `uwh_ipod_cp_*` | Defined functions and call sites: `HONDA_STATIC_CONFIRMED` for an in-process path | authentication thread and device state; exact lifecycle open |
| Auth function → I²C coprocessor channel | `os_auth_cp_obtain` → config/open/ioctl; `os_auth_cp_read/write` → `i2c_read_write` | binary call sites plus matching preserved config: `HONDA_STATIC_CONFIRMED` | process-local fd and mutex |
| Auth result → iAP2 authenticated flag | `auth_result` → `ios_iap2_set_authenticated` | direct call at `0x170d92`: `HONDA_STATIC_CONFIRMED` | iAP2 device state |
| iAP2/CarPlay attach → AirPlay control | `mc_carplay_*_iap2_attached`, `AirPlayReceiverServer*` | both inside `jmcs`; exact object transfer `UNKNOWN` | `UNKNOWN` |
| AirPlay request → Setup/response | `AirPlayReceiverSessionSetup` and serializer | [R3A](43t1-r3a-setup-path-seam-map.md): `HONDA_STATIC_CONFIRMED` | receiver session |

The earliest exact hardware edge is the configured I²C channel in the preserved image. The chain is not a demonstrated external handoff. Neither the authentication thread nor `jipod_set_authenticated` alone proves the later AirPlay pairing state; that edge remains open.
