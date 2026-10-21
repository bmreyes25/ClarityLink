# Type111 security and licensing boundaries

- REA 6.7.0 is distributed under MIT; see the [official repository](https://github.com/morluto/rea/tree/7c6c25dda75e2d1d595a6cacc5cf9a82607f8502).
- xcertplay at [`1298fb3`](https://github.com/shilapi/xcertplay/tree/1298fb35e29ee30e7bd849cb0e751b52aa22a13f) declares GPL-3.0. This campaign publishes findings and links, not copied implementation code. Any future reuse requires a separate license and compatibility review.
- Ghidra is Apache-2.0 licensed. No commercial Hopper/IDA license was installed.

xcertplay's self-signed HTTPS and all-interface listener require deliberate network isolation and trust handling. Source-level Origin/Host checks are not user authentication. Do not expose such a bench service to untrusted networks. The campaign did not connect a phone or run the service.

REA is an analysis tool, not authority to access a target. Keep firmware, private symbols, captures, credentials, identifiers, and Honda-derived details in authorized private storage. Tool execution may be local while prompts or tool output can still enter an agent/provider context; assess that boundary before analyzing sensitive material. No credential extraction, authentication bypass, private Binder invocation, firmware modification, CAN, Honda ADB, or vehicle operation is authorized.

Attribution and source links are recorded in [provenance](source-provenance.md). Clean-room specifications reduce code-copying risk but do not guarantee legal permission.
