# R6F third-party dependency review (@ECC)

No third-party implementation was vendored or executed in R6F. The selected future integration candidate is LIVI + LIVI Link.

| Project | Source/version | License | Reuse / reference | Security and maintenance review |
|---|---|---|---|---|
| LIVI | https://github.com/f-io/LIVI; current public `main` docs reviewed 2026-10-05; exact commit must be pinned before integration | GPL-3.0 (verify exact repository LICENSE at pin) | Reference macOS CarPlay receiver stack; future narrow adapter should expose authenticated session/control ownership. No code copied. | Source available, public project currently active. ECC review required before reuse: network bindings, plist/parser bounds, secret and pairing handling, update/provisioner trust, lifecycle, GPL obligations, Type111 capability and API stability. |
| LIVI Link provisioner/firmware | Same repository, LIVI-LINK.md; exact release/firmware hash not selected | Project license governs tools; firmware blobs require individual license/provenance check | Future use to provision compatible user-owned dongle; no firmware run in R6F. | Flashing is a mutating firmware operation; require compatible model, stock backup, signed/hash-verified official release, and user authorization at acquisition. |
| OCBM | https://github.com/lvalen91/ocbm; current docs reviewed 2026-10-05 | Unlicense per project documentation | Referenced for CPC200 architecture; no code reused | Full adapter ownership prevents desired ClarityLink `/info` control handoff; firmware/provisioning security review would be needed. |
| xcertplay | https://github.com/shilapi/xcertplay; current public README reviewed 2026-10-05 | GPL-3.0 per repository | Compared only; no code reused | Android-first/signing service candidate; lawful chip/service and host integration remain unresolved. |

ECC boundary: no external firmware, binaries, auth blobs, certificates or private identity entered the repository. Before future integration pin source commit, inspect LICENSE/dependencies, narrow the API adapter, and review trust, network scope, malformed-input bounds, timeouts, logging redaction, close ownership and reconnect.
