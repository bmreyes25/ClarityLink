# R7E target dependency audit

**Status:** `BLOCKED_BY_ARTIFACT`. No R7E target diagnostic was built, so there is no NEEDED/import list to classify.

| Dependency class | Current evidence | Classification / action |
|---|---|---|
| Android API17 platform libraries | Must be read from eventual ELF and checked against NDK API17 stubs | `API17_STANDARD` only after audit |
| Project-bundled libraries | Must be identified in final artifact manifest | `BUNDLED_PROJECT` only after audit |
| Honda static components | Not required by the intended platform-only diagnostic; no Honda service dependency may be assumed | `HONDA_STATIC_EVIDENCE` only with exact preserved evidence |
| Any other NEEDED/import | No artifact exists | `UNKNOWN`; mandatory unknown blocks Test A |

No Honda binary, `jmcs`, USB, iAP2, MFi, `/dev/i2c-2`, startup service, or privileged dependency is approved for the diagnostic. NDK r23c must be configured and its exact version recorded before offline build. No transfer destination or shell privilege is assumed; `/data/local/tmp` availability and writable semantics remain `EVIDENCE_REQUIRED`.
