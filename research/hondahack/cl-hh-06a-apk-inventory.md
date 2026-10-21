# CL-HH-06A — HondaHack APK inventory and REA readiness

**Status:** APK located and structurally inspected offline. REA/JADX CLI runtime verified. Codex MCP Android tools require a desktop restart and a fresh live call before they can be marked ready. No vehicle access was performed; `safeForHonda() == false`.

## Scope and provenance

This report records a bounded offline investigation of the previously preserved HondaHack Pro 7.7.7 APK and a harmless self-authored APK smoke target. Raw APKs, exact hashes, private evidence IDs, local paths, decompilation, and signing details remain in authorized private storage. The public report does not establish installation authenticity or the identity of the original signer.

## Recovery outcome

An earlier filename search reported no APK. A bounded search of the existing ClarityLink private preservation inventory located the previously preserved artifact. Its SHA-256 matched the historical private note. REA/JADX accepted the artifact and returned a complete decoded manifest and package inventory. Archive integrity checking found no compressed-data errors.

Observed package metadata: package `cn.autohack.hondahack`, version name `7.7.7`, version code `1`, minSdk `17`, targetSdk `17`; one DEX, 1,292 classes, 1,022 resources, three ARMv7 native libraries, and Xposed integration indicators. These are static artifact observations. REA reported signature verification as not performed. A local JAR-signature verifier could not establish a valid APK signature, so signer identity and signature validity remain **UNKNOWN**. The artifact's completeness is supported by successful package parsing and archive integrity, but installation provenance is not established.

## Toolchain readiness

| Layer | Result | Evidence and limit |
|---|---|---|
| Host | Apple Silicon macOS | Host architecture and OS recorded privately. |
| REA | `rea-agents` 6.7.0 available | CLI runtime calls succeeded. |
| Java | OpenJDK 21, full JDK | `java`, `javac`, `jdk.compiler`, and a self-authored compile/run check succeeded. Existing Homebrew JDK reused. |
| JADX provider | `jadx-headless-mcp` 0.7.1 | Official release JAR verified against REA's pinned SHA-256; ZIP and required provider class checked. |
| REA CLI Android analysis | **RUNTIME VERIFIED** | Harmless self-authored APK passed package, class search, class/method inspection, and reference-trace operations with Evidence IDs. Target was not executed. |
| Codex REA MCP Android | **REQUIRES RESTART / RECHECK** | A live Android call against the old MCP process returned `jar_configured=false`. Persistent REA config now references the verified provider; restart Codex Desktop and repeat the live Android call. MCP readiness is not claimed. |
| Ghidra | 12.1.4 available | Prior native smoke result is separate and does not prove Android readiness. |
| Apktool | Optional, unavailable | REA/JADX decoded the manifest; no additional apktool step was needed. |
| Android SDK inspection tools | Not found on PATH | Not required for the performed REA/JADX inventory. No ADB was run. |

A reproducible host-side check is provided in [`tools/doctor_re_toolchain.sh`](../../tools/doctor_re_toolchain.sh), with setup and interpretation notes in [`REA Android toolchain`](../../docs/development/rea-android-toolchain.md). The doctor is read-only and does not install packages, execute an APK, or claim that a running Codex MCP inherited changed settings.

## Inventory coverage

The decoded manifest was inspected before targeted class analysis. The private evidence set includes the manifest and component inventory, DEX/native inventory, Xposed indicators, selected feature-toggle and lifecycle methods, and references around selected entry points. Exact component names and implementation references are withheld. The public Display 1 architecture findings and their limits are in [`CL-HH-06B`](cl-hh-06b-display1-data-flow.md).

## Evidence class and limitations

- **OBSERVED_STATIC:** package/version/SDK metadata, manifest decode, DEX/resource/native inventory, feature-toggle behavior, selected Xposed lifecycle structure, and selected screenshot/rendering pipeline stages.
- **OBSERVED_HISTORICAL_RUNTIME:** only the previously preserved, limited historical observation described in earlier private research; it does not generalize to all warnings or failure states.
- **INFERRED:** high-level producer/consumer relationships where static references connect stages but do not establish runtime ordering or successful cluster presentation.
- **UNKNOWN:** signer identity/authenticity, caller authorization contract, warning priority, physical navigation viewport, crash-safe restoration, and bus side effects for unexecuted service paths.
- **UNSUPPORTED:** a documented, supported third-party Display 1 renderer-admission API was not established.
- **REQUIRES_AUTHORIZATION:** any vehicle-facing runtime validation or invocation of private vehicle services.

## Next exact task

Restart Codex Desktop, then make a fresh actual REA MCP Android inspection call on a harmless self-authored APK and verify manifest, class/method inspection, references, and Evidence IDs. Record that result separately from the successful CLI evidence. Continue CL-HH-06B only with offline static evidence until a supported interface and safety contract are independently established. `safeForHonda() == false`.
