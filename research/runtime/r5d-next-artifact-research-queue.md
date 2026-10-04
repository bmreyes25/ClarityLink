# R5D lawful next research queue

| Priority | Candidate | Next public/offline step | Stop rule |
|---|---|---|---|
| P0 | None | No authenticated public payload passed the gate. | Do not download a mirror as if it were publisher-hosted. |
| P1 | EU Civic MRC12.4 | Seek a public Honda-hosted copy of ST-10-005-02 or public publisher hash/manifest for `MRC_EU_SW_v12_4.zip`; seek archived *public* PANEX metadata without login or endpoint guessing. Compare bulletin model codes and region with any independently sourced package metadata. | If only PANEX-gated original and forum mirror exist, retain `QUARANTINE_METADATA_ONLY`. |
| P1 | US Civic 2016/2017 19-101 | Search later NHTSA bulletin revisions and public Honda publications for explicit package name/hash linked to `1.F197.60` / `1.F196.39` and exact trim/head-unit part. | No VIN, dealer system or fabricated vehicle data. |
| P2 | 2021 Civic `1.F1A5.15` | Find official year/trim build or part record; identify whether vcm30t30a and 1115 are actually the same receiver branch. | Do not infer ancestry from version string. |
| P2 | Clarity public parts identity | Seek a public Honda service bulletin or label/parts source that maps exact preserved target part to MY16ADA build `1.F1A2.45`; compare with Civic supplier/platform identifiers. | A catalog replacement number is not the preserved unit's actual label. |
| P3 | Accord and Acura | Retain official program/version notes; search only for specific supplier/SoC/receiver part evidence. | Stop if only CarPlay/cluster feature similarity appears. |
| P3 | CR-V MY16ADA owner report | Seek official bulletin or public parts corroboration. | Forum report alone is not lineage proof. |
| P4 | Unauthenticated forum mirrors, dealer-only payloads, low-trim unrelated HUs | Metadata only or reject. | No payload acquisition until custody/access gate passes. |

Next milestone should close the original publisher hash/custody gap for the named EU package, or find a different public publisher-hosted update. R3C runtime NO-GO remains binding.
