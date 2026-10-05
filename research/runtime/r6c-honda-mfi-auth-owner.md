# R6C factory authentication owner

Evidence level: `HONDA_STATIC`. The preserved `jmcs` SHA-256 is `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; `libcarplay_proxy.so` is `dc8bc5c19cf32a8e7edcc14c1d80e78bb96ca6ccc434229349c74590136bef66`. Both are ignored local inputs. No live Honda system was queried.

**Decision: `R6C_AUTH_INTERNAL_TO_JMCS`.** The authentication implementation, iAP2 authentication state, and CarPlay receiver reside in the same `jmcs` ELF. This identifies the software owner in the preserved build, not the hardware chip manufacturer or a supported external API.

| Connected evidence | Interpretation | Confidence |
|---|---|---|
| `mc_carplay_app_init` calls `mc_carplay_proxy_auth_register@plt` at `0xb03d2`; the proxy exports `proxy_uwh_ipod_cp_{obtain,get_certificate,set_challange,get_signature,...}` and stores one callback record | The proxy is a process-local callback facade for Honda's accessory-auth operations. It is not itself the hardware owner. | `HONDA_STATIC_CONFIRMED` |
| `mc_carplay_uwh_ipod_cp_obtain` calls `uwh_ipod_cp_obtain` at `0xad920`; `uwh_ipod_cp_*` call `os_auth_cp_*`; `os_auth_cp_read/write` call `i2c_read_write` | CarPlay authentication reaches a hardware-backed I²C path inside `jmcs`. | `HONDA_STATIC_CONFIRMED` |
| `auth_thread` calls `uwh_ipod_cp_*` and `jipod_set_authenticated`; `auth_result` calls `ios_iap2_set_authenticated` at `0x170d92` | The same executable coordinates accessory authentication and iAP/iAP2 state. The two auth flows need not be identical. | `HONDA_STATIC_CONFIRMED` |
| `os_auth_cp_obtain` reads `IPOD_I2C_AUTH_CHANNEL_FILE` and `IPOD_I2C_AUTH_SLAVE_ADDR`, then calls `open` and `ioctl`; preserved `j_config.xml` gives `/dev/i2c-2` and `0x10` | A specific configured I²C hardware path exists. The exact device actually opened at runtime is unobserved. | `HONDA_STATIC_CONFIRMED` for code/config; `UNKNOWN` runtime |

`libcrypto` alone was not used to infer MFi ownership. Certificate and signature API names are corroborated by the call chain above. No certificate, signature, challenge, key, or device serial was read or retained. The precise relationship between iAP accessory authentication and subsequent AirPlay control-session pairing remains unresolved.
