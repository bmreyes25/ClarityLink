# 43T1-R5C — public Honda/Acura artifact provenance expansion

## Scope and decision

R5C began only after the R3 inventory, local recovery record, state normalization, and Phase A clean commit `07621b1c8c08a7e15c12037bd17427b6767c035c`. Its research remained public and offline. It found a new official, exact Civic version/compatibility lead, but no lawful analyzable receiver package.

**R5C research decision:** `R5C_NEW_HIGH_CONFIDENCE_ARTIFACT_LEAD_FOUND`

**Technical recommendation:** `GO_FOR_R5D_ARTIFACT_PROVENANCE_CLOSURE`

**Stop condition:** B — Honda's public bulletin 19-101 materially narrows the next provenance search to an exact 2016/2017 Civic package pair and affected trims. The bulletin authenticates the version metadata, not a binary. R5D should seek an original public package URL/archive and independently verify custody and analysis terms; it must not use a dealer login, fabricated VIN, vehicle data, or an unverified forum mirror.

## Baseline and safety ledger

| Item | Result |
|---|---|
| Starting HEAD | `2e32be77d18064080980ce96a6e77e3bbb88ba70` |
| Concurrent independent R5Y HEAD before Phase A commit | `a88d67960cb692c9058662b1757c73529133e80b` |
| Repo hygiene commit | `07621b1c8c08a7e15c12037bd17427b6767c035c` |
| Final implementation / verification HEAD | To be filled after commits and hosted checks |
| Branch / repo hygiene | `main`; `R5C_REPO_CLEAN` at Phase A boundary |
| R3 disposition | Six historical R3 draft files preserved and committed; later R3C controls |
| State normalization | One current action; R5B latest completed public research baseline, R5Y separate host model |
| Honda contacted / ADB used / vehicle connected | NO / NO / NO |
| Runtime reads / runtime writes | 0 / 0 |
| APK installed / `jmcs` modified / Type111 used on Honda / HondaHack runtime used | NO / NO / NO / NO |

## Public sources and findings

1. [Honda bulletin 19-101 revision 2](https://static.nhtsa.gov/odi/tsbs/2019/MC-10169058-0001.pdf) is `OFFICIAL_SOURCE`. It identifies 2016–17 Civic 2-door/4-door EX, EX-T, Touring as affected, failed-part number `39101-TBA-A21`, dealer Honda Firmware Downloader selection by vehicle VIN, and resulting `1.F197.60` for 2016 and `1.F196.39` for 2017. Its [prior revision](https://static.nhtsa.gov/odi/tsbs/2019/MC-10166786-0001.pdf) independently corroborates the versions. No package URL, hash, receiver list, or head-unit ROM type is published in those bulletins.
2. [Honda bulletin 16-100](https://static.nhtsa.gov/odi/tsbs/2017/SB-10108290-9340.pdf) confirms an earlier 2017 Civic dealer USB update and explicitly excludes hatchbacks. It adds a model/trim split, not an analyzable artifact.
3. [Honda's public USB portal](https://usb.honda.com/index.html?lang=en) requires a vehicle-generated `update_by_usb` or `.json` file before offering a vehicle-specific package. The public page does not expose a historic package list. R5C did not submit a file or query the package endpoint.
4. [ic1101's public README](https://github.com/librick/ic1101) identifies most 2016–21 Civics as a Tegra 3 / Android 4.2.2 / Mitsubishi Andromeda family, excluding lower trims with different units. Its [update notes](https://github.com/librick/ic1101/blob/main/docs/updates.md) list `1.F1A5.15` on a 2021 EX hatchback, `1.F197.70` for an update file, and the `SwUpdate.mdt` naming convention. This is `PUBLIC_RESEARCH`, not publisher custody of a package or permission to use one. R5C did not download the repository's proprietary-derived payloads or build/update tooling.
5. [CivicX forum version posts](https://www.civicx.com/forum/threads/infotainment-software-update.16505/page-48) were `FORUM_LEAD` only. They mention package folders, `1.F197.60`, `1.F196.39`, and older versions such as `1.F194.30`; they do not authenticate a mirrored binary. No forum package was downloaded.
6. [Honda's Accord release](https://hondanews.com/en-US/honda-automobiles/releases/release-97d09069e73c229822892485de000817-honda-enhances-ownership-experience-with-upgrade-to-wireless-apple-carplay-and-android-auto-for-2018-2022-accord-models) establishes a dealer-installed wireless CarPlay/Android Auto upgrade for eligible 2018–22 wired-only Accords. [Honda's 2025 dealer notice published by NHTSA](https://static.nhtsa.gov/odi/tsbs/2026/MC-11026971-0001.pdf) names accessory `08A43-TVA-100` and a license-file issue. [Honda's 2018 Accord press kit](https://hondanews.com/en-US/releases/2018-honda-accord-press-kit-overview) describes an Android-based Honda HMI and available HUD. None establishes `jmcs`, the exact receiver family, or a public firmware payload. Accord-to-Clarity lineage remains `UNKNOWN`.
7. [Acura's 2019 RDX OTA release notes](https://owners.acura.com/Documentum/ota/2019_RDX.pdf) give `D.1.2.1` and discuss CarPlay, meter/HUD, and a secondary display. [2020 RDX notes](https://owners.acura.com/Documentum/ota/2020_RDX.pdf) add public version metadata, including a TCU-specific `FDC17.07.007 / NAD200.0.9A00`. The notes expose no receiver package or proof of vcm30t30/`jmcs` lineage. RDX is a lower-priority `UNKNOWN` branch.
8. [Honda bulletin 20-021](https://static.nhtsa.gov/odi/tsbs/2021/MC-10187522-0001.pdf) concerns 2019–20 Civic LX audio/HFL software; this lower-trim branch lacks evidence of the target receiver family and is ranked P3.

The [candidate table](../research/runtime/r5c-public-artifact-candidates.md), [provenance graph](../research/runtime/r5c-public-artifact-provenance-graph.md), [public update workflow](../research/runtime/r5c-honda-public-update-workflow.md), and [acquisition gate](../research/runtime/r5c-public-artifact-acquisition-gate.md) keep official version facts separate from package provenance.

## Artifact and Type111 result

- Best new candidate: the 2016/2017 Civic bulletin 19-101 update pair, exact official versions `1.F197.60` / `1.F196.39` and defined 2/4-door trim scope. Its package location remains dealer-gated, and no public binary has been authenticated.
- Strongest existing family lead: 2021 Civic EX Hatchback `1.F1A5.15` / Andromeda-vcm30t30, as public research metadata. No exact package or payload found.
- Artifact obtained / filename / size / SHA256: **NO / N/A / N/A / N/A**.
- Receiver component found: **NO artifact to inspect**; no claim that a package lacks one.
- Type111 dispatch, response, connection ID, listener, security, media, screen, and teardown: `UNKNOWN`. Type110 coexistence on a descendant: `UNKNOWN`.
- R5X adapter evidence map: not created; there is no real candidate component to map.

Compared with R5B, R5C adds official Civic year/trim/version and failed-part metadata, distinguishes dealer and consumer update channels, and records separate Accord/Acura version branches. It does not close the receiver payload or Type111 evidence gate.

## Verification and governance

ECC evidence review separated `OFFICIAL_SOURCE`, `PUBLIC_RESEARCH`, `FORUM_LEAD`, and unauthenticated package claims. Official version confidence is high; binary custody and analysis permission remain unresolved. No literal `111`, marketing feature, or forum filename was promoted to Honda receiver evidence.

Focused checks: R5Y preserved-work tests 95 passed; R5C provenance table/source and current-state cross-links reviewed. Full suite: 811 passed, 3 skipped; 3 standard-library smoke checks and simulator checks passed. Repository health: passed with 546 Markdown files, 128 indexed reports, 0 curated broken links, and 0 forbidden tracked extensions. `git diff --check`: passed. Offline CI, CodeQL, final HEAD, and final worktree status are recorded after hosted verification. Phase A repository repair report: [hygiene decision](43t1-r5c-repository-hygiene-and-state-normalization.md). Rules v2 remains governing; R3C runtime `jmcs`/Type111 NO-GO and R4D Display 1 possible-but-unproven status remain unchanged. Next milestone is R5D provenance closure, public/offline only.

No Honda/ADB/runtime work was performed. R5C repaired and normalized repository state and continued lawful public Honda/Acura artifact research only. It does not authorize a vehicle experiment, Type111 negotiation, or jmcs modification.
