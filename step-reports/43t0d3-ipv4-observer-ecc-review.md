# Step 43T0-D3 — offline IPv4 observer repair and ECC review

**Decision: `43T0_D3_NETCFG_ECC_GO` for a separately initiated read-only 43T0-D observation.** Starting HEAD: `54d04dbbcd19f81e424f260c2ebd578a5e452f3d` on clean `main`. This D3 milestone contacted no Honda, ran no ADB, and made zero target writes. It did not run the collector, connect CarPlay, create a listener, negotiate Type111, or change Honda runtime. The prior D2 private capture remains host-only and immutable.

## Cause and source classification

The D2 command `ifconfig` exited 0 with zero stdout and stderr bytes after four successful baseline reads. [Android 4.2.2_r1 Toolbox `ifconfig.c`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1/toolbox/ifconfig.c) returns 0 immediately for zero arguments. A one-interface argument enters getter ioctl operations, but extra arguments can mutate network state. This AOSP behavior is `EXTERNAL_PRIOR_ART` / `EXTERNAL_STATIC_SEMANTICS`; D2 itself establishes only the observed empty Honda result. Empty output does not establish failed ADB, failed networking, absent interfaces, or a broken utility.

[Android 4.2.2_r1 `netcfg.c`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1/netcfg/netcfg.c) sends zero arguments to `dump_interfaces()`: it enumerates `/sys/class/net`, retrieves IPv4 address, prefix, flags, and hardware address, and prints one row per interface. `dhcp`, `up`, `down`, `flhosts`, `deldefault`, and `hwaddr` are argument-driven actions. These source facts remain `EXTERNAL_PRIOR_ART` until matched to preserved Honda firmware.

## Preserved Honda static compatibility

The ignored, preserved `system-vendor.tar` was inspected read-only. Its sole `system/bin/netcfg` member is a regular ELF, mode `02750`, uid 0, gid 3003, size 5,500 bytes, SHA-256 `ea204431f664a32e44d890373ccf16c952a921e2c98cd5e0387b2bbc429c00db`. It is a stripped 32-bit little-endian ARM EABI5 dynamic executable with `/system/bin/linker`; imports include `libc.so`, `libnetutils.so`, `libstdc++.so`, and `libm.so`. A host-only [inventory check](../tools/step43t0d3_static_review.py) returns `HONDA_PRESERVED_NETCFG_PRESENT` and pins this exact binary hash. The prior D2 identity evidence contains the binary's group 3003; this is a sanitized group-membership fact, with no raw `id` line committed.

Static strings and imports include `/sys/class/net`, `opendir`, `readdir`, `closedir`, `ifc_get_info`, `ifc_get_hwaddr`, `UP`, `DOWN`, the IPv4/prefix/flags output format, and action names. Thumb disassembly shows an `argc == 1` branch into the interface enumeration routine, while the action dispatch is on the other branch. This independently supports the AOSP zero-argument behavior as **`HONDA_STATIC_COMPATIBILITY`**, not `OBSERVED_ON_HONDA_READ_ONLY`. The live command and exact output remain unobserved. If live `netcfg` is unavailable, malformed, nonzero, oversized, or timed out, D0-3 stops and preserves partial evidence with no fallback.

| Candidate | Honda static evidence | Fixed command | IPv4 to interface mapping | Privacy | Complexity | ECC result |
|---|---|---|---|---|---|---|
| Zero-argument `netcfg` | Present; matching static control flow | Yes | Yes | MAC stripped from derived output | Low | Selected |
| One-interface `ifconfig` | Toolbox symlink; AOSP getter semantics only | Dynamic per interface | Yes | Raw interface data | Medium | Rejected: unnecessary dynamic command and argument surface |
| Omit IPv4 observation | N/A | None | No | Lowest | Low | Rejected: safe static-supported observer exists |

## Versioned command and analysis contract

Collector version **`43T0-D0-3`** retains one host enumeration, seven identity reads, five-second command timeout, 64-KiB combined output cap, historical endpoint and identity gates, three human-gated phases, owner-only host capture, reconnect stop, and no retries. The only phase-command replacement is `("shell", "ifconfig")` with exact `("shell", "netcfg")`. The new [D3 plan](../tools/step43t0d3_netcfg_plan.py) is source-hash pinned, and the collector manifest records that hash. The fixed phase sequence, repeated for baseline, connected, and post-disconnect, is:

1. `cat /proc/net/dev`
2. `cat /proc/net/route`
3. `cat /proc/net/ipv6_route`
4. `cat /proc/net/if_inet6`
5. `netcfg` with **zero arguments**

The collector's exact argv allowlist rejects every additional `netcfg` token and excludes zero-argument `ifconfig`; no fallback or diagnostic command was added. The [offline analyzer](../tools/analyze_43t0d_capture.py) dispatches by pinned collector version. D0-1/D0-2 partial captures keep their historical `ifconfig.raw` schema; D0-3 expects `netcfg.raw` and its revised-plan hash. The real D2 capture was revalidated read-only as `CAPTURE_VALID_PARTIAL` and `IDENTITY_MATCH`, with no completed phase or invented IPv4 mapping. Its manifest hash remained unchanged.

The [strict netcfg parser](../tools/step43t0d_offline.py) bounds bytes and lines, requires strict UTF-8 and the Android 4.2 row structure, validates state/flags and IPv4/prefix, rejects duplicate interfaces, and retains `0.0.0.0` explicitly without treating it as a usable bind address. MAC values can appear only in the private raw capture: the parsed model drops them, public JSON/Markdown omit them, and the privacy scanner rejects a leaked MAC or ADB endpoint. The IPv6 route parser still accepts repeated valid rows; set-based phase deltas prevent duplicate rows from amplifying G11 evidence. G11-F cannot be promoted by observational evidence.

## ECC-method threat review and verification

Accidental mutation and argument creep are blocked by the exact fixed suffix allowlist and direct argv. Wrong utility semantics are bounded by preserved Honda binary inspection, AOSP comparison, and a live fail-closed format gate. Parser overacceptance is constrained by strict row shape, field validation, and input caps. Privacy is enforced by owner-only raw storage, MAC elision, and derived-output scanner. Contract drift is caught by plan/source hashes and command-equivalence tests. Static evidence is never labeled live Honda observation. This is an ECC-method review using the ECC security-review skill; no independent reviewer sign-off is claimed.

Focused D3/DPREP/collector tests: **110 passed**. Full configured offline suite: **525 passed, 3 skipped**, plus the self-locator smoke and simulator checks. Tests include absent/unresolved archive paths, fixed 15-read contract, identity and reconnect stops, no fallback, malformed/oversized/UTF-8 netcfg, MAC stripping, old-capture acceptance, versioned D0-3 validation, and duplicate IPv6 route set semantics. `git diff --check` passed. Source and privacy checks are recorded by this review; hosted CI is to be verified after push.

**Exact next step:** separately initiate 43T0-D parked-car read-only observation under the updated [one-page runbook](../research/runtime/43t0d-live-runbook.md), with already-reviewed ADB connection precondition and exactly one intended Honda target. After collector exit, issue the mandatory CAR-OFF message before offline analysis. No 43T1 or runtime/deployment authorization follows from D3.
