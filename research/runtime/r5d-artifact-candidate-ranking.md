# R5D candidate ranking

Scores are research-priority heuristics (0–5), **not evidence**. Columns: Clarity relevance (C), receiver family (F), CarPlay (P), cluster (K), official provenance (O), public access (A), exact version (V), static analyzability (S), Type111 information value (T). A score cannot make an inaccessible or unauthenticated artifact analyzable.

| Candidate | C | F | P | K | O | A | V | S | T | Sum | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| EU Civic MRC12.4 / `1.F197.70` | 4 | 4 | 5 | 2 | 3 | 1 | 4 | 1 | 4 | 28 | P1 metadata; original PANEX package gated, mirror quarantine |
| US 2016 Civic / `1.F197.60` | 4 | 4 | 5 | 2 | 5 | 0 | 5 | 0 | 4 | 29 | P1 official version; VIN/dealer package missing |
| US 2017 Civic / `1.F196.39` | 4 | 4 | 5 | 2 | 5 | 0 | 5 | 0 | 4 | 29 | P1 official version; VIN/dealer package missing |
| 2021 Civic EX HB / `1.F1A5.15` | 3 | 4 | 5 | 2 | 1 | 0 | 3 | 0 | 4 | 22 | P2 public research metadata |
| 2018 Clarity target | 5 | 5 | 5 | 4 | 3 | 0 | 4 | 0 | 5 | 31 | Baseline, no public descendant package |
| 2018–22 Accord upgrade | 1 | 0 | 5 | 4 | 5 | 0 | 0 | 0 | 1 | 16 | P3 separate HMI; lineage unknown |
| 2019–20 Acura RDX | 1 | 0 | 5 | 4 | 5 | 0 | 4 | 0 | 1 | 20 | P3 OTA metadata only |
| 2020 CR-V Hybrid MY16ADA forum lead | 2 | 2 | 3 | 0 | 0 | 0 | 1 | 0 | 2 | 10 | P3 unverified owner metadata |

The EU Civic package identity is the best *package-provenance* lead because a reproduced bulletin gives publisher channel, exact name, vehicle codes, version and approximate size. The US pair has stronger official version proof. None passes the [acquisition gate](r5d-public-artifact-acquisition-gate.md).
