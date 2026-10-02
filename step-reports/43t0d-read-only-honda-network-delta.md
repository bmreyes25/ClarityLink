# Step 43T0-D — read-only network delta, fail-closed preflight

**Decision: `43T0_D_NO_GO`.** Starting HEAD: `b3451ca3850e537fc32e42105fbbc4977228646c`, clean `main`. On 2026-10-02 at 10:13:54 PDT (17:13:54 UTC), the reviewed collector `43T0-D0-1` began the separately initiated live attempt. The operator had said the parked Honda was ready, but the one permitted host enumeration returned **zero ADB targets**. The collector exited `AMBIGUOUS_ADB_TARGET` before the parked-Honda confirmation or any target command. Thus **ADB used = YES (host enumeration only); Honda contacted by a target command = NO; target writes = 0**. Physical readiness was user-reported, not technically verified.

## CAR-OFF boundary and evidence integrity

Immediately after the collector exited, before analysis or Git work, Codex told the operator: **“CAR MAY BE TURNED OFF NOW. No further Honda or ADB commands will be used in this milestone.”** The message followed the 17:13:54 UTC collector exit; its exact delivery timestamp was not independently captured. No Honda or ADB command was issued afterward. No retry, new endpoint scan, connection troubleshooting, or fresh run occurred.

The operator later reported that the car was connected. This arrived **after** the CAR-OFF boundary, so collection did not resume. Codex instructed the operator to turn the car off normally and kept the remainder of the milestone offline.

The private host bundle is `~/CLARITY_43T0D_20261002_171347`, outside Git. Directory mode is `0700`; `manifest.json` and `preflight/devices.raw` are `0600`. The raw files remain host-only. The manifest records the expected project commit, approved-plan commit, and collector source SHA-256 `2162e795568307cfe34dbf7bc8a6de1f70d358119e4aca22e9c6e29789809afc`. Its final status is `AMBIGUOUS_ADB_TARGET`. Exactly **one** command ran: the approved host `adb devices` enumeration, index 1, return status 0, `SUCCESS` as a command, 26 stdout bytes and 0 stderr bytes. Saved stdout SHA-256 matches manifest value `36f15c2fe32964a6fbe902e914a47739d4e6304b0d3e812bf08096ff0419b7ae`; the parsed target count is zero. No endpoint identifier is retained here. Seven identity reads and all 15 network reads were **not run**; baseline, connected, and post-disconnect phases were **not captured**. Final center/audio/cluster sanity was not reached; the operator may turn the vehicle off normally.

## G11 analysis boundary

There is no new interface, IPv4, IPv6, route, or socket evidence to parse. The existing [40E analysis](43t0a-40e-network-evidence-reanalysis.md) remains the only real-Honda stock-CarPlay network correlation; 43P remains separate Mac/iPhone/PlayPort evidence. This attempt establishes only that the currently visible ADB device list was empty at enumeration time. It does not show whether Honda networking changed or why the ADB route was unavailable.

| Gate | Result after 43T0-D | Reason |
|---|---|---|
| G11-A interface identity | `NO` | No new interface read. |
| G11-B Honda local address | `LIKELY_INFERRED` | Prior 40E link-local socket correlation only; no address-to-interface map. |
| G11-C address family | IPv6 candidate; final `UNKNOWN` | Prior 40E evidence only. |
| G11-D route topology | `NO` | No route read. |
| G11-E `jmcs` socket ownership | `NO / READ_BLOCKED_WITHOUT_PRIVILEGE` | No ownership read was approved or attempted. |
| G11-F new listener reachability | `NO` | No listener or bind test. |

**Candidate binding policy:** none can be promoted from this attempt. The 40E IPv6 candidate still requires an observed interface/scope and route before a specific-address policy can be designed without guessing. Exact missing fact: a current, unambiguous ADB target in `device` state, followed by the approved identity gate and three-phase network delta in a *separately initiated* session. This milestone will not recollect.

## ECC method review, privacy, and reversibility

The ECC evidence-first, command-boundary, privacy, and fail-fast review finds the collector obeyed the 43T0-C/D0 contract: one host enumeration, fail closed on zero targets, no target command, no fallback, no extra capture. There was no independent external ECC reviewer capability; this is the documented ECC-method review. Evidence classification is `HOST_ONLY_OBSERVED` for the zero-target enumeration and `UNRESOLVED` for all intended Honda network facts. The private raw output and any endpoint/identifier remain outside Git; committed evidence contains only the target count, approved command class, status, timing, byte counts and hashes.

`NO_INTENTIONAL_MUTATION_OCCURRED`; `TARGET_WRITES = 0`; `ROOT_USED = NO`; `SU_USED = NO`; `TYPE111_ACTIVITY = NONE`; `LISTENER_CREATED = NO`; `JMCS_MODIFIED = NO`; `RUNTIME_ATTACHMENT = NO`. This does not claim zero physical state change from normal operator or ADB-host activity. No ClarityLink rollback is required.

**Next milestone:** offline ECC review of the existing ADB-over-Wi-Fi connection precondition and the smallest separately initiated retry plan, without adding target commands or changing Honda networking. The live 43T0-D session ended at the CAR-OFF boundary; no further vehicle action is authorized by this report.
