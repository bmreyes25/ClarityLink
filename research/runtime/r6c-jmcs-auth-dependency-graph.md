# R6C jmcs authentication dependency graph

Input identity and evidence convention: [auth owner](r6c-honda-mfi-auth-owner.md). All edges are static. `HONDA_STATIC_CONFIRMED` means visible in the preserved build; `PROBABLE` and `UNKNOWN` are explicit limits.

| Dependency / path | Class | Evidence | Boundary |
|---|---|---|---|
| `libexpat`, `libbinder`, `libstagefright`, `libstagefright_foundation`, `libmedia`, `liblog`, `libutils`, `libmedia_native`, `libcarplay_proxy`, `libgui`, `libc`, `libstdc++`, `libm`, `libudev`, `libmdnssd`, `libcrypto`, `libnetutils`, `libOpenSLES`, `libdl` | GENERIC plus AUDIO/SCREEN/TRANSPORT candidates | Exact `DT_NEEDED` in [dependency graph](jmcs-dependency-graph.md) | Library presence alone proves no specific auth path. |
| `libcarplay_proxy.so` | AUTHENTICATION/AUDIO/SCREEN | `DT_NEEDED`, PLT registration calls; [proxy audit](r6c-libcarplay-proxy-audit.md) | Process-local callback dispatch, not external handoff. |
| `jiap_usb_host_mode_transport_*`, `process_udev_dev_usb_device`, `libudev` | TRANSPORT | defined symbols plus library dependency | In `jmcs`; physical fd not recovered. |
| `ios_iap2_*`, `iap2_core_attach`, `iap2_acc_auth_*` | IAP2/PAIRING | defined symbols and internal call sites | In `jmcs`; no external handle. |
| `uwh_ipod_cp_*` → `os_auth_cp_*` → `i2c_read_write` | AUTHENTICATION | call sites and I²C config | In `jmcs`; configured hardware path. |
| `AirPlayReceiverServer*`, `AirPlayReceiverSession*`, request/response serializer | CONTROL_SESSION/SCREEN/AUDIO | symbols and R3A/R3C direct call graph | In `jmcs`. |
| `CarPlayApService` Binder | DISPLAY/INPUT/GENERIC | manifest and decompiled AIDL | UI/status, no raw CarPlay request or session FD. |

Other inventory: generic `dlopen/dlsym` sites were traced to SQLite/dynamic support by [R3C](jmcs-dlopen-sites.md); no CarPlay plugin target was recovered. The preserved path `/vendor/media/mcs/j_config.xml` supplies `IPOD_I2C_AUTH_CHANNEL_FILE=/dev/i2c-2` and slave address `0x10`; USB role sysfs strings include `tegra-otg` and `tegra-udc`, but their use at runtime is unknown. Binder `JMediaCore::IJIpcService/IJIpcChannel` symbols exist; their payloads have not been shown to carry authenticated CarPlay control. UDP/TCP/Unix socket endpoint ownership, properties, JNI bridges, launch service name, UID/GID, and FD transfer are `UNKNOWN` unless cited above. Their absence from this graph is not negative proof.
