# Type 111 renderer handoff contract

Candidate flow: Type111 receiver/parser -> candidate decrypt/config/H.264 extraction -> decoder (ownership/API unknown) -> owned decoded frame -> future process-local ExternalDisplay adapter -> Display 1 composition.

Transport currently yields Annex-B H.264 access units, not pixels. The offline renderer input contract is positive dimensions, RGBA_8888, byte row stride, presentation timestamp in nanoseconds, optional rotation/crop, and owned CPU bytes or an explicit surface token. The prototype Display 1 target is 800x480; physical navigation safe area, crop/mask and UI overlap remain unknown. None of these prototype details is a Type111 wire fact.

Require bounded frame ownership, stale-generation rejection and clear/close on Type111 teardown. Do not acquire/modify center Display 0. Preserve required cluster safety UI; composition policy remains unknown.

- Target renderer seam: process-local ExternalDisplay host adapter, architecture target only.
- Current executable seam: digital twin/mock backend.
- Supported companion frame API: not found in reviewed interfaces.
- Host mock test: ready; Android/vehicle render test: not ready.
- Unknowns: decoder/surface ownership, pixel transfer, geometry, host entry, lifecycle and authorization.
