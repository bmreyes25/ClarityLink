# 43T1-R5B — Honda descendant artifact and Type111 static triage

## Scope and result

R5B was an offline/static and lawful public-artifact research milestone. It did not use a vehicle or acquire any binary. The strongest public lead is the 2021 Civic EX Hatchback 4D update metadata `1.F1A5.15` for the 2016–2021 Civic family described by the public `ic1101` research project as Tegra 3 / ARMv7, Android 4.2.2, Mitsubishi Andromeda. The repo distinguishes its MIT original work from proprietary Honda/Mitsubishi code/data. The official Honda USB portal requires a vehicle-generated data file. No publicly available, versioned receiver payload with sufficiently clear provenance/analysis terms was identified.

**R5B decision:** `R5B_NO_LAWFUL_ANALYZABLE_ARTIFACT_FOUND`

**Project recommendation:** `GO_FOR_MORE_PUBLIC_ARTIFACT_RESEARCH`

This is not a negative Type111 finding. The candidate is `TYPE111_INSUFFICIENT_ARTIFACT` because no descendant receiver binary was available to inspect.

## Baseline and worktree

- Starting HEAD: `06ff680e9f665da909fd7887cd98908c3b348465`
- Final HEAD: pending milestone-owned commit / hosted verification
- Branch: `main`
- Pre-existing user changes: modified `EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, `step-reports/README.md`, plus untracked R3 drafts. These were preserved and must not be swept into a commit.
- Worktree at report drafting: pre-existing changes plus R5B files and appended state updates; no Honda artifacts.

## Safety ledger

| Action | Result |
|---|---|
| Honda contacted | NO |
| ADB used | NO |
| Runtime reads | 0 |
| Runtime writes | 0 |
| Vehicle connected | NO |
| APK installed | NO |
| `jmcs` modified | NO |
| Type111 used on Honda | NO |
| HondaHack runtime used | NO |
| Firmware/package downloaded | NO |
| Target binary executed | NO |

No Honda/ADB/runtime work was performed. No experiment was authorized.

## Search scope and sources

Reviewed public project documentation and update metadata from [librick/ic1101](https://github.com/librick/ic1101), including its [README](https://github.com/librick/ic1101) and [update notes](https://github.com/librick/ic1101/blob/main/docs/updates.md); the [official Honda USB update portal](https://usb.honda.com/index.html?lang=en); public Civic bulletin/forum references; and prior R5A/R3C/R4D/R5X project evidence. Search included Civic years 2016–2021, the Accord 2018–2022 branch, Acura sibling leads, `jmcs`, Andromeda, MediaCore, receiver/screen symbols, and Type111 signatures.

The official portal’s vehicle-data requirement was not satisfied or bypassed. Forum/MediaFire payload references were not downloaded because provenance/terms were unclear. No private or restricted source was accessed.

## Artifact candidates and provenance

- **Best candidate:** 2021 Civic EX Hatchback 4D, `1.F1A5.15`, release-keys, ROM type 1115, as listed in public research notes.
- **Best candidate SHA256:** N/A — no payload obtained.
- **Secondary candidate:** public update metadata `1.F197.70`, release-keys, ROM type 2250; exact vehicle/build relation not established.
- **Backup:** official Honda public USB update portal; package query requires vehicle-generated data unavailable under this milestone.
- **Excluded:** forum/mirror package references, marked `PROVENANCE_UNCLEAR`; no download.

See [acquisition log](../research/runtime/r5b-artifact-acquisition-log.md), [lineage map](../research/runtime/r5b-honda-receiver-lineage-map.md), and [candidate ranking](../research/runtime/r5b-candidate-artifact-shortlist.md).

## Lineage and components

The public Civic project states that it covers most 2016–2021 Civic head units, excluding some trims with different head units, and reports Tegra 3, ARMv7, Android 4.2.2, and Mitsubishi Andromeda. This makes the Civic EX metadata a high-confidence related family lead, not proof of exact Clarity binary identity or implementation portability. Accord/Acura lineage remains unknown without exact platform/build evidence.

No descendant `jmcs`, receiver library, APK/JAR/ODEX, or ELF component was available for R5B inventory. No hashes, architectures, imports, exports, strings, or symbols were generated. Artifact inventory and control-flow notes are therefore not applicable; no artifact was altered or executed. See [component identification](../research/runtime/r5b-receiver-component-identification.md) and [descendant/Clarity comparison](../research/runtime/r5b-descendant-vs-clarity-comparison.md).

## Type111 signatures and control flow

No Honda descendant code was available to test SETUP dispatch, type-111 response construction, data endpoint creation, stream identity consumption, second screen registration, per-screen security, listener/media path, teardown, or distinct Type110 preservation. None of these is marked present or absent. The correct artifact-level classification is `TYPE111_INSUFFICIENT_ARTIFACT`.

No control-flow trace is claimed. R5A’s signature checklist remains the re-entry criteria. External AES-era receiver findings remain `EXTERNAL_PRIOR_ART` and were not promoted to Honda evidence. See [static triage](../research/runtime/r5b-type111-static-triage.md), [evidence gate](../research/runtime/r5b-honda-descendant-evidence-gate.md), and [external prior-art cross-check](../research/runtime/r5b-external-prior-art-crosscheck.md).

## Governance and decisions

Rules v2 is adopted and compliant. R3C still controls `jmcs`/Type111 runtime NO-GO. R5X remains `MODEL_ONLY`. R4D ordinary-app Display 1 remains possible but unproven. No vehicle action, ADB, APK, listener, Type111 negotiation, runtime attachment, HondaHack, framebuffer, or patch is authorized.

Decision matrix: continue lawful public artifact/provenance research. Deeper static analysis and Clarity architecture comparison become actionable only after an analyzable, versioned lawful payload is obtained. See [R5B next-path matrix](../research/runtime/r5b-next-path-decision-matrix.md).

## Verification record

- ECC findings: evidence labels kept distinct; no lineage/metadata/marketing/external evidence was elevated to Honda Type111 implementation proof.
- Focused checks: public-source/provenance review and R5B document cross-link/repository-health checks passed; no binary tooling was run because no candidate artifact was obtained.
- Full suite: 716 passed, 3 skipped; standard-library smoke checks 3 passed; simulator checks passed.
- Repo health: passed — 523 Markdown files, 0 broken links in curated docs, 0 forbidden tracked file extensions.
- `git diff --check`: passed.
- Offline CI: pending; verify only on the exact pushed milestone commit.
- CodeQL: pending; verify only on the exact pushed milestone commit.

## Next milestone

`GO_FOR_MORE_PUBLIC_ARTIFACT_RESEARCH` — seek a lawfully accessible, versioned, reviewable descendant receiver artifact without vehicle interaction, credentialed access, or bypass. If none appears, keep the Honda Type111 route parked. R3C’s runtime NO-GO is unchanged.

No Honda/ADB/runtime work was performed. R5B is lawful public-artifact and static receiver research only; it does not authorize a car experiment or a `jmcs` patch.
