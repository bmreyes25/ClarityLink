# CL-FACTORY-01 / M1 — Factory artifact inventory & tool readiness

Status: IN PROGRESS. Evidence class per item. Offline static only; no vehicle. `safeForHonda() == false`.
Exact SHA-256 values, local paths, and the precise build fingerprint/model are recorded in authorized **private**
storage (per `docs/security/public-private-evidence-boundary.md`) and are not reproduced here.

## Platform identity (PROVEN_STATIC)
- Preserved image: Honda ADA (Andromeda-class) head unit. Android **4.2.2 / API 17**, `armeabi-v7a` (+`armeabi`).
- A private build manifest records the exact fingerprint, model code, and build id; all components below were
  SHA-256 inventoried into that private manifest (377 files). Originals were read-only; none modified or executed.

## Component inventory (PROVEN_STATIC presence)
| Family | Components | ABI/format | Notes |
|---|---|---|---|
| CarPlay receiver apps | `CarPlay.apk`(+odex), `CarPlayService.apk`(+odex) | APK + ODEX | pkg `com.mitsubishielectric.ada.app.carplay` (CarPlay) |
| Navigation | `Navigation.apk`(+odex), `NavigationLib`(odex) | APK + ODEX | |
| External display | `ExternalDisplayApService.apk`(+odex), `ExternalDisplayOutService.apk`(+odex), `ExternalDisplayLib.jar`(+odex) | APK/JAR + ODEX | HondaHack view-insertion host per CL-HH-06 (not a supported API) |
| CarPlay API lib | `CarPlayApServiceApiLib`(odex) | ODEX | |
| Native receiver/display | `jmcs`, `libcarplay_proxy.so` (+ surfaceflinger/libgui/libui/libbinder/libandroid_runtime) | ELF ARM EABI5 | `jmcs`, `libcarplay_proxy` **unstripped, with debug_info** |
| Framework | `framework.jar`, `services.jar`, `android.policy.jar` (+ full boot ODEX set) | JAR + ODEX | 32 boot `.odex` present |

## APK/ODEX pairing & build matching (PROVEN_STATIC)
- All factory APKs and framework JARs are **code-stripped**: the APK/JAR contains `AndroidManifest.xml` + resources
  but **no `classes*.dex`**; executable code lives in the paired `.odex` (magic `dey\n036` — Dalvik optimized DEX).
- The complete boot-classpath ODEX set (framework, android.policy, services-equivalent, etc.) is present, which is
  the prerequisite for a deterministic deodex. APK↔ODEX pairing is 1:1 by basename.
- Observed custom OEM permission on the CarPlay app: `com.mitsubishielectric.ada.permission.VEHICLE_RW` (declared;
  grant/enforcement semantics are `UNKNOWN` pending the framework graph).

## Tool readiness (this environment)
| Capability | State | Evidence |
|---|---|---|
| REA/JADX Android (manifests/resources) | **AVAILABLE** | JADX 0.7.1 opened `CarPlay.apk`: manifest complete, package/permissions/resources extracted |
| REA/JADX Android (Java code graph) | **BLOCKED** | odex-separated → `class_count=1`; code not in APK. Needs deodex first. |
| Deodex (Dalvik API17) | **TOOL REQUIRED** | no `baksmali`/`smali`/`apktool` installed; boot ODEX set is present, so deodex is feasible once the tool is obtained |
| Native (Ghidra 12.1.4) | **AVAILABLE** | confirmed on first-party native earlier; CL-SYS-01A already analyzed `jmcs`/`libcarplay_proxy` |

This resolves the CL-SYS-01A "REA/JADX unavailable" gap **for manifests/resources**; the Java call graph remains
gated on the deodex step rather than on JADX availability.

## Verification summary
- SHA-256 identity: recorded (private manifest). Platform/ABI: API17 / ARMv7 (PROVEN_STATIC). Build matching: all
  components share the one preserved image; boot ODEX set complete (deodex-ready). Missing dependencies: none found
  for deodex. Mixed-build uncertainty: the preservation note does not certify all partitions contemporaneous (carried
  from CL-SYS-01A).

## M1 → M2 bounded next steps
1. Obtain a Dalvik-API17-capable deodex tool (e.g. `baksmali` 2.x `deodex` with the preserved bootclasspath) into an
   isolated tool directory; deodex the five factory APKs + `ExternalDisplayLib`/`NavigationLib` to DEX **privately**.
2. Extract and publish (sanitized) the manifest/component/permission surface for all factory APKs (CarPlay app
   manifest already extractable; others pending the same pass).
3. Native: re-confirm `jmcs → libcarplay_proxy` boundary and the singleton screen-registration finding against the
   exact preserved binaries (Ghidra) for M2/M5.

No deodex, decompilation, or native output is published; all raw analysis remains private.
