# R6C libcarplay_proxy audit

`jmcs` directly loads the preserved proxy (`dc8bc5c19cf32a8e7edcc14c1d80e78bb96ca6ccc434229349c74590136bef66`). The proxy needs only `libexpat`, `libc`, `libstdc++`, and `libm`. Its `mc_carplay_proxy_auth/audio/screen_register` exports accept callback records; `jmcs` has corresponding PLT relocations and calls auth registration during `mc_carplay_app_init` at `0xb03d2`. The proxy's `proxy_uwh_ipod_cp_*`, `AudioStream*`, and `ScreenStream*` exports forward to those records. [R3C detailed audit](43t1-r3c-libcarplay-proxy-interface-audit.md) shows screen's second registration returns an error and unregister clears the global six-word callback record.

Auth registration is a genuine **internal** interface, but its producer is `jmcs` and its consumer is the same process's receiver. The proxy does not open the I²C device, maintain the authenticated session, or export a Binder/socket channel. Its auth callback record is not an independent authentication service, and replacing it would disturb the factory receiver. No safe external consumer or session transfer is evidenced.

**Answer:** application/native callback glue, not the reusable authenticated transport boundary sought for ARCH_A. Clean-room ABI description is limited to conceptual callback groups; no proprietary header or implementation was copied.
