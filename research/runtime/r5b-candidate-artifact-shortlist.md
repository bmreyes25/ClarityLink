# R5B — candidate artifact shortlist

Scores are 0–5; a low provenance score blocks acquisition regardless of total. Public metadata alone does not count as a receiver artifact.

| Rank / candidate | Lineage proximity | Artifact availability | Version recency | Cluster-CarPlay evidence | jmcs probability | Receiver-library availability | Static-analysis usefulness | Provenance confidence | Total / 40 | Disposition |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| TOP CANDIDATE — 2021 Civic EX Hatchback 4D, `1.F1A5.15` | 5 | 2 | 4 | 2 | 5 | 1 | 4 | 3 | 26 | Public notes strongly place it in the vcm30t30/Andromeda family; payload not obtained and repo notes do not relicense Honda data |
| SECONDARY CANDIDATE — public `ic1101` update-file line `1.F197.70` | 4 | 2 | 3 | 1 | 4 | 1 | 4 | 2 | 21 | Exact vehicle/build relation not established; no payload acquisition |
| BACKUP CANDIDATE — official Honda USB update portal, vehicle-specific branch | 3 | 1 | 4 | 2 | 2 | 1 | 3 | 5 | 21 | Official source, but requires vehicle-generated file; unavailable under offline/no-vehicle boundary |
| LOW-VALUE CANDIDATE — Accord 2018–2022 updates | 2 | 1 | 4 | 3 | 1 | 1 | 2 | 4 | 18 | No proven Clarity/Civic receiver lineage or public binary |
| LOW-VALUE / EXCLUDED — forum bulletin / MediaFire references | 2 | 3 | 3 | 1 | 2 | 2 | 2 | 0 | 15 | Payload provenance/terms unclear; do not download |

## Ranking rationale

The 2021 Civic EX is strongest because public technical notes tie the covered Civic family to the same old Android/Tegra/Andromeda architecture and provide a versioned example. It remains metadata-only until a specific, lawful, reviewable payload is available. Official access quality cannot overcome the vehicle-file prerequisite. Accord is not assumed equivalent. Forum-hosted payload mirrors are excluded even where availability appears higher.

**TOP CANDIDATE:** Civic EX Hatchback 4D 2021, `1.F1A5.15` metadata lead.

**SECONDARY CANDIDATE:** `1.F197.70` update metadata.

**BACKUP CANDIDATE:** official Honda portal, if an authorized public package can be accessed without vehicle interaction or bypass.

**LOW-VALUE CANDIDATE:** Accord and unproven Acura families; forum/MediaFire package references are excluded on provenance grounds.

@ECC recommendation: continue public source and rights research; do not represent any candidate as acquired or analyzed.
