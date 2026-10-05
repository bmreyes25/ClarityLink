# R6C1 public MFi oracle research

Apple's [accessory verification description](https://support.apple.com/guide/security/verifying-accessories-sec70a4f377d/web) describes a hardware authentication IC furnishing an accessory certificate and responding to a challenge. It also describes MFi-SAP for CarPlay video secure association. These are public architecture facts, not proof of Honda's implementation.

[xcertplay](https://github.com/shilapi/xcertplay/blob/master/README.md) separates an authenticator from receiver transport and lists native I²C, USB bridge and remote backends. [OCBM](https://github.com/lvalen91/ocbm) separates iAP2, pairing/authentication and receiver components around genuine hardware. Their code was not copied. OCBM's component split does not establish that Honda exposes a service or that the factory device can be shared while `jmcs` runs.

R6D's hash-matched Honda static trace supplies the separate Honda evidence: `APSMFiSAP_Exchange` calls `APSMFiPlatform_CreateSignature` and `APSMFiPlatform_CopyCertificate`; those resolve `proxy_uwh_ipod_cp_*` symbols from `/system/lib/libcarplay_proxy.so`; the proxy callback goes to `uwh_ipod_cp_*` and `os_auth_cp_*`. See the [R6D call graph](r6d-honda-mfi-oracle-callgraph.md). The target candidate is an opaque factory certificate/signature oracle with ClarityLink owning iAP2 and AirPlay; it remains unexecuted.
