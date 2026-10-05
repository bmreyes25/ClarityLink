# R6D Honda MFi oracle call graph

Input: local ignored `jmcs`, SHA256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; local ignored `libcarplay_proxy.so`; preserved `j_config.xml`. Offsets are `jmcs` virtual addresses. Calls were read offline using `llvm-nm` and `llvm-objdump`. No target execution occurred.

| Caller / edge | Callee / observation | Classification |
|---|---|---|
| `APSMFiSAP_Exchange` `0x299db8` | `APSMFiPlatform_CreateSignature` `0x28d86c` at `0x299f44`; `APSMFiPlatform_CopyCertificate` `0x28d938` at `0x299f52` | `HONDA_STATIC_CONFIRMED` |
| `APSMFiPlatform_Initialize` `0x28d6ac` | `dlopen` at `0x28d6b4`; literal string at `0x33402f` is `/system/lib/libcarplay_proxy.so`; `dlsym` resolves `proxy_uwh_ipod_cp_*` names from adjacent literals | `HONDA_STATIC_CONFIRMED` |
| `APSMFiPlatform_CreateSignature` | obtain → submit challenge → poll readiness → signature length/body → release, through resolved function pointers; rejects a challenge longer than 20 bytes at `0x28d882` | `HONDA_STATIC_CONFIRMED` sequence; ABI details `PARTIAL` |
| `APSMFiPlatform_CopyCertificate` | obtain → certificate length/body → release, through resolved function pointers | `HONDA_STATIC_CONFIRMED` sequence |
| `mc_carplay_app_init` | `mc_carplay_proxy_auth_register` at `0xb03d2`; registered `mc_carplay_uwh_ipod_cp_*` callbacks call `uwh_ipod_cp_*` | `HONDA_STATIC_CONFIRMED` |
| `uwh_ipod_cp_*` | `os_auth_cp_*` read/write/obtain/release/ready | `HONDA_STATIC_CONFIRMED` |
| `os_auth_cp_obtain` `0x27bd7c` | config lookup → `open` → `ioctl(0x703, configured address)` → process-global fd | `HONDA_STATIC_CONFIRMED` |
| `os_auth_cp_read/write` | `i2c_read_write` → host I²C fd | `HONDA_STATIC_CONFIRMED` |
| `auth_thread` | same `uwh_ipod_cp_*` certificate/challenge/signature family → `jipod_set_authenticated`; `auth_result` → `ios_iap2_set_authenticated` | `HONDA_STATIC_CONFIRMED` |

`libcarplay_proxy.so` is an **in-process callback facade**, not an independently callable external auth service. The dynamic load edge corrects the earlier R3C loader survey's SQLite-only scope; that older negative finding missed `APSMFiPlatform_Initialize`. It does not create a transferable session handle. Certificate, challenge and signature buffers belong to the individual call and are released on exit; no value was copied into this report. Error-code mapping and ABI stability remain unknown.
