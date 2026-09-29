# CarPlay Screen device instance

## Proven caller

`mc_ScreenStreamStart` calls `mc_dev_attach` at `0xBDC06` with the exact key `"CarPlay Screen"` (literal VA `0x2E0340`) and a stream-associated second argument loaded from `[r6 + 0x78]`. The manager allocates an attach record and scans registered interfaces as described in [device-registration.md](device-registration.md).

## Device identity and instance

| Field | Finding |
|---|---|
| Request name | `CarPlay Screen` — exact string and callsite confirmed |
| Winning registration | Unknown; callback scores are not recovered for this key |
| Attach callback | Unknown for this key |
| Device instance type | Unknown; manager allocates a generic `0x20`-byte record in `devmgr_dev_alloc` |
| Stream argument mapping | Generic allocator writes the newly created secure pointer through the argument; exact API type/stream-field owner unknown |
| Detach implementation for this entry | Unknown |
| Duplicate-name/multiple-instance result | Unknown |

The generic manager allocates a `0x20`-byte record, creates a secure pointer to it with `j_secure_ptr_create` (`0x123DB4`), stores that pointer at record `+0x0c`, and writes it through the second `mc_dev_attach` argument. The selected entry pointer is retained in the per-attach record after attach success. This is evidence for a per-attach manager record, not proof that the concrete media device, sink, decoder, or Surface is independent. The generic manager object itself is reached through a global pointer by `mc_dev_attach`.

`media_dev_attach` and `media_dev_attach_cb` are real generic media symbols, and media registration plumbing is present. Neither is attributed to the `CarPlay Screen` key absent a recovered successful comparator result and registration initializer.
