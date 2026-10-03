# Step 43T0-D4 — read-only Honda network observation

**Result:** `CAPTURE_VALID`; identity matched; all three approved phases completed. G11-A through G11-D are supported by read-only observation. The PREP2 specific-address binding engine returned `BIND_POLICY_READY`. G11-E remains `NO / READ_BLOCKED_WITHOUT_PRIVILEGE`; G11-F remains `NO`. This result does not establish Type111 acceptance, Honda listener reachability, or runtime readiness.

## Start state and authorization

- Date: 2026-10-03. Starting HEAD: `a0710ed55bc07963b496a5ae19cfc932bbd26b6a`, branch `main`, clean and matching `origin/main`.
- Verified D0-3 collector, plan, analysis tools, and PREP2 artifacts were unchanged from the post-PREP2 repository baseline. The collector source, D3 plan, approved-plan source, 40E manifest, and pinned ADB binary passed their existing hash gates.
- The user confirmed the Honda was parked and stationary, normally powered, physically present, connected over the established Mac network path, and in normal center-display/audio/cluster state with wired CarPlay disconnected.
- Scope was only the separately authorized 43T0-D/D4 read-only observation. No Type111 negotiation, RAM attachment, `jmcs` modification, listener creation, root/`su`, `ptrace`, `/proc/<pid>/mem`, installation, CAN, USB injection, system modification, or vehicle-control change occurred.

## Bounded collection

Collector `43T0-D0-3` used the checksum-pinned ADB executable and verified historical 40E manifest. The single reviewed ADB-over-Wi-Fi prerequisite succeeded; there was no scan, alternate target, retry, or troubleshooting. The collector performed its own one-device enumeration and matched all seven identity reads to the expected Android 4.2.2 / API 17 / `vcm30t30a` / `Andromeda` / `vcm30t30` identity and pinned shell/kernel fingerprints before network reads. Collector source SHA-256: `a156f7707462714872b49e917231385cd3562cd6ed54da64314f8fc53745fccd`; D3 plan SHA-256: `68ec3ccd3ff69d533bdee3d3d38dc2df389015ba960e9effa10450776f68647f`.

The collector then captured exactly the five reviewed files in each phase: `/proc/net/dev`, `/proc/net/route`, `/proc/net/ipv6_route`, `/proc/net/if_inet6`, and zero-argument `netcfg`. Baseline was disconnected, connected was normal wired CarPlay, and post-disconnect was the returned stock state. The `netcfg` invocation succeeded with bounded, parseable output in all three phases; no MAC values appear in derived data. The sequence comprised one host enumeration, seven identity reads, and 15 network reads. Target writes: **0**. Privilege: unprivileged shell only; root/`su`: **NO**.

The identity and command gates passed. The offline analyzer classified the capture `CAPTURE_VALID` / `IDENTITY_MATCH`, with complete baseline, connected, and post-disconnect phases and the exact 23-command manifest. Raw capture and private binding detail remain in owner-only directories outside Git. Exact IP addresses, MACs, and the ADB endpoint are withheld from this report and repository.

After post-disconnect reads, the user confirmed CarPlay disconnected and stock center display, audio, and cluster normal. Immediately after collector exit, the operator issued: **CAR MAY BE TURNED OFF NOW. No further Honda or ADB commands will be used in this milestone.** No Honda or ADB command was run afterward.

## Network findings

One strong phase-correlated candidate was observed on interface `usb0`, which remained present across the three phases. One scoped IPv6 link-local address and four distinct supporting non-default IPv6 route rows appeared with connected CarPlay and reversed after disconnect. The route/address/interface tuple passed the analyzer's scope and interface consistency checks. No IPv4 address/route pair met the phase-correlation criteria for a candidate; the fixed IPv4 observations remain in the private raw capture. D4 also matches the IPv6 link-local address class correlated with stock CarPlay in the verified 40E socket evidence. This is system-wide network correlation; it does not establish `jmcs` socket ownership.

| Gate | Result | Evidence boundary |
|---|---|---|
| G11-A — phone-facing interface identity | `YES_OBSERVED` | One address/route candidate on `usb0` tracks the connected phase and reverses on disconnect. |
| G11-B — Honda local address | `YES_OBSERVED` | Exact value is held only in the private capture/binding detail. |
| G11-C — address family | `IPv6` | The phase-correlated address is IPv6 link-local. |
| G11-D — route topology | `YES` | Supporting non-default route rows match the candidate interface and address scope. |
| G11-E — `jmcs` socket ownership | `NO / READ_BLOCKED_WITHOUT_PRIVILEGE` | D4 did not read process-owned descriptors. |
| G11-F — listener creation/reachability | `NO` | D4 creates no listener and makes no connection attempt to one. |

The analyzer labels the candidate `HONDA_OBSERVED_NETWORK_POLICY_INPUT`, not Type111 confirmation. The offline PREP2 `evaluate_binding` engine accepted the captured specific-address IPv6 evidence as `BIND_POLICY_READY`: `BIND_INTERFACE=usb0`; `BIND_ADDRESS` resolved from the private capture and withheld here; `ADDRESS_FAMILY=IPv6`; link-local `SCOPE_ID` required and matched to the observed interface index; `ROUTE_POLICY` supported by the connected-phase route. Wildcard binding remains rejected. This makes PREP2's network-policy placeholders complete without proving that a Honda process can create or reach a production listener.

## ECC-guided review and verification

ECC security-review, fail-closed, evidence-classification, and privacy guidance was applied manually. Review confirmed the fixed command surface, successful identity gate before network reads, exact phase order, lack of fallback/retry, no target writes, and separation between Honda network observations and Type111/runtime claims. No independent ECC reviewer service was available; this is not an independent external audit.

- Direct offline evaluation of the private D4 network-policy input: `BIND_POLICY_READY`; address values remained in process/private storage.
- Focused D0-3 parser/collector, route/duplicate-route, analyzer, and PREP2 model/integration tests: **227 passed**.
- Configured offline suite: **642 passed, 3 skipped**; self-locator **3/3 passed**; configured simulator checks passed.
- Analyzer privacy gate: passed with exact addresses and MACs withheld. Repository health checker: passed with 110/110 eligible milestone/support reports indexed and no broken curated links. `git diff --check`: passed.
- Sanitized D4/R0 records were committed and pushed to `main` in `03faacae9ce34d7f358d5dbe7a2fed423c2700c2`. Hosted [Offline CI](https://github.com/bmreyes25/ClarityLink/actions/runs/37136534247) passed; hosted [CodeQL](https://github.com/bmreyes25/ClarityLink/actions/runs/37136534210) passed for all five configured languages.

## Boundary and next action

D4 closes the read-only network mapping prerequisite, not the overall live-listener contract. Actual Bionic listener behavior and iPhone reachability, Honda process-memory permission/mechanism, Honda CoreFoundation response ownership, target rollback/restoration, Type111 acceptance, and Type111 framing/security remain unproven. No live modifying experiment is authorized by D4. See [43T1-R0 post-D4 readiness review](43t1-r0-post-d4-readiness-review.md) for the fresh gate matrix and decision.
