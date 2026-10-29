# CL-FACTORY-01 / M2a — Deodex pipeline & build analysis

Status: COMPLETE (pipeline). Evidence OBSERVED_STATIC. Offline only; `safeForHonda() == false`.
Exact hashes, decompiled/smali output, and proprietary identifiers are in authorized **private** storage.

## Deodex capability (resolves the CL-SYS-01A Java-graph blocker)
CL-SYS-01A could not analyze the factory Java graph because the APKs are ODEX-separated and no deodex tool was
available. That is now resolved:

- Tool: `baksmali` 2.5.2 (pinned), obtained from Maven Central; artifact + all runtime dependencies
  (`dexlib2`, `util`, `guava`, `failureaccess`, `jcommander`) **SHA-1-verified** against their published Maven
  checksums, kept in an isolated private tool directory. Run under the project's private Temurin JDK 21.
- Method: `baksmali deodex -a 17 -d <boot-classpath-dir>` against **copies** of the preserved ODEX plus the full
  preserved boot-classpath ODEX set (78 framework/vendor `.odex`). Preserved originals were never modified.
- Result: clean deodex (exit 0) across the factory receiver/navigation/external-display components.

## Deodexed component sizes (OBSERVED_STATIC)
| Component | Deodexed classes |
|---|---|
| CarPlay.apk | 55 |
| CarPlayService.apk | 106 |
| CarPlayApServiceApiLib | 74 |
| Navigation.apk | 275 |
| NavigationLib | 118 |
| ExternalDisplayOutService.apk | 907 |
| ExternalDisplayLib | 17 |
| ExternalDisplayApService.apk | 27 |

## Build compatibility
- All components deodex deterministically against the one preserved boot classpath (API 17 / Dalvik), confirming a
  single self-consistent build. No missing boot dependency was encountered during deodex.
- Output is retained privately as smali (and can be assembled to DEX for JADX on a per-class basis where a readable
  Java view is needed). No decompiled/smali output is published.

## Limitations
Deodex reconstructs the DEX from the optimized form; it is faithful to the preserved image but is not runtime proof.
Proprietary class/method identifiers are retained privately per `docs/security/public-private-evidence-boundary.md`.
