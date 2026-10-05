# R6D iAP2 and AirPlay authentication link

The iAP2 `auth_thread` calls `uwh_ipod_cp_obtain`, reads the certificate, submits a challenge, polls signature readiness, reads the signature and sets iPod authentication state. The AirPlay `APSMFiSAP_Exchange` invokes platform certificate/signature wrappers; `APSMFiPlatform_Initialize` resolves the factory `proxy_uwh_ipod_cp_*` symbols from the registered proxy, leading to the **same** `uwh_ipod_cp_*` and `os_auth_cp_*` implementation.

Decision: `R6D_AUTH_PRIMITIVE_SHARED` **at the static code and hardware-access path**. This does not prove that a single concurrent session or external process can safely use the primitive. It also does not establish proprietary iAP2 or MFi-SAP message compatibility in ClarityLink. The factory Type110 screen key is derived from AirPlay receiver-session material and streamConnectionID as recorded in R6C; a direct key derivation from the IC was not found.
