# Step 43T0-A — offline 40E network / G11 reanalysis

**Decision: `40E_PARTIAL_PRECISE_DELTA_REQUIRED`. Next action: `RETURN_TO_ECC_WITH_EXACT_DELTA_PLAN`.** Starting HEAD `10d39e5998f9c8018639b26a4bb4636683d10b0f` on clean `main`. `HONDA_CONTACTED = NO`; `ADB_USED = NO`; `TARGET_WRITES = 0`; `NO_INTENTIONAL_MUTATION = YES`. This analysis creates no Honda rollback requirement and authorizes no vehicle session.

## Provenance and phase mapping

The immutable host-only bundle `~/CLARITY_RUNTIME_20260929_195051` and adjacent prior analysis JSON are present outside Git. Its manifest names 1,943 artifacts. All 1,944 entries in `sha256.txt` (artifacts plus manifest) verified with zero failures. The manifest's `phase_order` is `baseline`, `connected`, `connected_maps`, `post-disconnect`; only the three named network phases have socket snapshots. The intermediate `connected_maps` operation is not a fourth network phase. Manifest times (UTC): baseline 2026-09-30 02:50:52–02:52:00; connected 02:52:51–02:53:54; post-disconnect 02:55:27–02:56:22. The manifest and the [40E report](40e-readonly-runtime-preflight.md) establish disconnected baseline, stock wired CarPlay connected, then disconnected. Each phase contains `network/{tcp4,tcp6,udp4,udp6}.raw` and corresponding `platform/proc_net_*` snapshots. The manifest records fixed `/proc/net/tcp*` and `/proc/net/udp*` reads. It records no `/proc/net/dev`, `/proc/net/route`, `/proc/net/if_inet6`, `ifconfig`, or `ip` address/route collection. No route hex exists to decode. The adjacent analysis JSON is a derivative and does not supply those missing facts.

40E is real Honda plus stock CarPlay with **no Type111**. 43P is Mac/iPhone/PlayPort with Type111 and Type110 and **no Honda**. Their evidence classes are separate.

## Interfaces, addresses, and routes

| Fact | Baseline | CarPlay connected | After disconnect | Classification |
|---|---|---|---|---|
| Interface names, state, RX/TX counters | Not captured | Not captured | Not captured | `UNRESOLVED` |
| Interface to IPv4 or IPv6 address mapping | Not captured | Not captured | Not captured | `UNRESOLVED` |
| IPv4 routes, gateways, masks, flags, metrics | Not captured | Not captured | Not captured | `UNRESOLVED` |
| IPv6 routes / interface scope | Not captured | Not captured | Not captured | `UNRESOLVED` |
| Specific local IPv6 link-local endpoint in global socket table | Absent | Present in several established entries | Persists in closing TCP entries | `OBSERVED_ON_HONDA_READ_ONLY`; phone-facing interpretation `INFERRED` |
| IPv4-mapped local endpoint in global socket table | Present; unrelated network class | Additional specific endpoint during connected phase | Additional endpoint absent | `OBSERVED_ON_HONDA_READ_ONLY`; interface and CarPlay role `UNRESOLVED` |

The connected IPv6 address is `fe80::/10`, so a future bind would need a proven interface scope. Exact address bytes, unrelated IPv4 addresses, peers, and MAC-derived identifiers are withheld from Git. A socket local address proves the host had an endpoint in that snapshot; it does not show the owning interface or whether it remains stable in another session. There is no evidence for a specific-address listener policy yet.

## Global socket comparison

Rows were decoded from the captured `/proc/net/{tcp,tcp6,udp,udp6}` hexadecimal endpoint fields; IPv4 bytes were reversed, and IPv6 bytes were reversed within each 32-bit word. Comparison uses local/remote endpoint plus state, omitting unrelated peer addresses and raw tables. `0A` is TCP LISTEN, `01` ESTABLISHED, `02` SYN_SENT, `04` FIN_WAIT1, and `08` CLOSE_WAIT. UDP table state codes are retained as kernel table values, not TCP meanings.

| Table | Baseline | Connected | After | Relevant transition |
|---|---:|---:|---:|---|
| TCP IPv4 | 6 | 6 | 6 | No endpoint/state tuple unique to connected phase; 3 listeners and 3 established rows each phase. |
| TCP IPv6 | 3 | 6 | 5 | Three specific link-local established connections appear while connected, including one on local port 5000; those same three are `04` after disconnect. A wildcard port 5000 listener persists in all phases. One other IPv4-mapped `02` row changes but is not attributable to CarPlay. |
| UDP IPv4 | 4 | 7 | 4 | Three loopback self-endpoints appear only while connected; no phone-facing claim follows. |
| UDP IPv6 | 2 | 5 | 2 | One specific link-local connected row and one additional wildcard port appear during CarPlay; the remaining difference is a duplicate multicast-service row. |

These are `HONDA_RUNTIME_CORRELATION` for stock CarPlay timing. The link-local TCP/UDP pattern is the strongest phone-facing **address-family candidate**, but no interface name can be ranked from 40E. Remote addresses and ephemeral ports add no necessary policy fact and are redacted here. Global socket rows are not process ownership evidence. The 40E `jmcs` PID/start time remained stable across phases; `/proc/<jmcs>/maps` and `/proc/<jmcs>/fd` were permission denied. Thus `jmcs` ownership is `READ_BLOCKED_WITHOUT_PRIVILEGE`; no permission retry is proposed.

## G11 decision

| Gate | Result | Reason |
|---|---|---|
| G11-A interface identity | `NO` | No interface inventory or address-to-interface mapping. |
| G11-B Honda local address | `LIKELY_INFERRED` | A specific link-local IPv6 socket address is observed, but its phone-facing role, interface scope, and stability are inferred. No bind-policy-ready address. |
| G11-C address family | `IPv6` candidate; final path `UNKNOWN` | Stock-correlated link-local rows strongly suggest IPv6 use; IPv4-mapped rows also exist, and route/interface evidence is absent. |
| G11-D route topology | `NO` | No route capture. |
| G11-E process ownership | `NO / READ_BLOCKED_WITHOUT_PRIVILEGE` | FD access denied; global tables cannot identify `jmcs`. |
| G11-F new listener reachability | `NO` | No bind or phone-originated reachability evidence. |

The exact missing observation for interface policy is a phase-tagged interface inventory, address-to-interface mapping (including IPv6 scope and Honda IPv4 address), and routes during disconnected baseline and stock CarPlay, ideally also after disconnect to establish reversal. No broad repeat of 40E is justified. A future *narrow* observation may be justified only after independent ECC review of the delta below; this milestone gives no GO for a car visit.

## Offline proposed delta only — do not execute

The [proposed delta dry run](../tools/step43t0a_delta_dry_run.py) prints the exact argument arrays and intended host capture paths from the verified 40E manifest. It contains **no ADB execution path**. Invoke it offline with `--dry-run --manifest ~/CLARITY_RUNTIME_20260929_195051/manifest.json --host-output ~/CLARITY_43T0_DELTA_PROPOSED`; it only prints the 15 planned records. The redacted argv template is below; the local dry run resolves the serial from the manifest. These arrays are a **design**, not commands run in this milestone. For each of `baseline`, `connected`, and `post-disconnect`, capture only:

```text
["adb", "-s", "<previously verified target serial>", "shell", "cat", "/proc/net/dev"]       -> <private-host-bundle>/<phase>/net-dev.raw
["adb", "-s", "<previously verified target serial>", "shell", "cat", "/proc/net/route"]     -> <private-host-bundle>/<phase>/net-route.raw
["adb", "-s", "<previously verified target serial>", "shell", "cat", "/proc/net/ipv6_route"] -> <private-host-bundle>/<phase>/ipv6-route.raw
["adb", "-s", "<previously verified target serial>", "shell", "cat", "/proc/net/if_inet6"]  -> <private-host-bundle>/<phase>/if-inet6.raw
["adb", "-s", "<previously verified target serial>", "shell", "ifconfig"]                  -> <private-host-bundle>/<phase>/ifconfig.raw
```

The serial placeholder must be resolved from a separately checked target identity before any later execution; it is not printed in committed evidence. A later executable collector would need fixed argv without shell interpolation, a 5-second per-read timeout, 64-KiB per-read output cap, a phase/time/argv/status manifest on the Mac, mode-0700 host directory, and no target files. This dry-run implementation writes no capture and performs no ADB call. If `ifconfig` is unavailable or its no-argument read semantics cannot be established at preflight, stop; do not substitute an unreviewed command. No root, `su`, wildcard proc reads, maps/FD retry, binary pull, socket dump, active probe, or target modification. The five commands are **`NECESSARY` / `READ_ONLY_SEMANTICS_ACCEPTABLE` with caveat** for interface counters, IPv4 route, IPv6 route, IPv6 address/interface mapping, and IPv4 interface address respectively. Their exact execution and utility support need a new ECC GO. Existing socket reads are **`REDUNDANT` / `REMOVE`**. `/proc/net/ipv6_route`, `/proc/net/if_inet6`, and `ifconfig` require explicit validation in that review because the prior 43T0 review did not approve them.

## ECC review and privacy

ECC's [43T0 preflight](43t0-ecc-preflight-review.md) required reusing 40E first, fixed read-only commands for only a proven gap, host-only raw storage, and no ownership/reachability promotion from global tables. This reanalysis follows that boundary. Final ECC-style review: the raw bundle is outside Git and checksum-verified; no target command was run; the report retains only counts, address family/class, relevant listener port, and phase changes. It excludes raw tables, exact link-local address, MAC, unrelated IPs/peers, Wi-Fi data, credentials, device identifiers, and other processes. The proposed delta needs a separate ECC safety/command review before use. G11 remains partial; G5/G12/G19/G21 decisions from 43S2 are unchanged. Honda Type111 acceptance, listener bind/reachability, security, media, CoreFoundation bridge correctness, and cluster rendering remain unknown.

**Next milestone:** submit the five-command offline dry run for a separate ECC review, resolving utility availability and exact capture implementation. Do not start 43T0 or 43T1 or visit the Honda under this decision.
