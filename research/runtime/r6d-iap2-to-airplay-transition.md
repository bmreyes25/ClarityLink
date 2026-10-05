# R6D iAP2 authentication to AirPlay transition

The newly narrowed static path in the hash-matched `jmcs` is:

```text
auth_result(iAP device, result)
  → ios_iap2_set_authenticated(iAP device)
  → jiap2_get_dev / j_device_get_owner_ctx
  → owner-context authenticated flag
  → do_attach(context, device)
  → j_device_add / j_device_probe_and_attach
  → [generic callback selection not fully resolved]
  → mc_ios_dev_attach → mc_carplay_attached
  → mc_carplay_audio_iap2_attached / mc_carplay_screen_iap2_attached
```

`auth_result` calls `ios_iap2_set_authenticated` at `0x170d92`. The callee resolves the iAP2 device (`0x16e814`), reads its owner context (`0x16e81c`), writes a local authenticated flag (`0x16e82a`), and may call `do_attach` (`0x16e948`). `do_attach` adds/probes an internal device. `mc_ios_dev_attach` directly calls `mc_carplay_attached` at `0xfd774` with an owner-context field; the exact generic-probe callback edge is not identified. `mc_carplay_screen_iap2_attached` stores the incoming pointer in a process global. Those are in-process pointers/state, not a socket or transferable session handle.

AirPlay startup is a separate path: `mc_carplay_app_init` creates `_AirPlayThread` with `pthread_create` at `0xb06b2`; `_AirPlayThread` creates `AirPlayReceiverServer` at `0xaec64` and runs its event loop. Later an AirPlay connection handler calls `AirPlayReceiverSessionCreate` at `0x28ae48`. No direct call or object pass from `ios_iap2_set_authenticated` to that constructor was found. The association between a particular attached iAP device and control connection may rely on internal state/phone networking, but its exact object is `UNKNOWN`.

This closes the **observed transition form** to local device state and generic attach. It does not prove every internal association edge, nor a supported external handoff. No private authentication material was inspected.
