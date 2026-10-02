> **D3 offline review:** `43T0_D3_NETCFG_ECC_GO` applies only to the versioned D0-3 observational contract. A future car session must be separately initiated. Zero-argument `netcfg` has static Honda compatibility; its live output remains unobserved.

# 43T0-D live runbook — separately initiated read-only retry

**Current precondition:** D2 stopped after zero-argument `ifconfig` returned zero bytes. Do not rerun D0-2. The D0-3 collector uses zero-argument `netcfg` with no fallback. Before any separately initiated attempt, confirm the parked car, intended Honda, and exactly one already-connected ADB target using the reviewed connection precondition.

1. Park the car. Head unit on, Mac connected, normal CarPlay disconnected. Have the immutable 40E manifest and the reviewed D0-3 collector. The host output path must be new and outside Git. Confirm the intended Honda in person.
2. After the connection precondition is satisfied, invoke only the reviewed collector:
   `python3 tools/step43t0d0_collector.py --host-output ~/CLARITY_43T0D_<timestamp> --execute-approved-43t0-delta --adb-path /opt/homebrew/bin/adb --historical-manifest ~/CLARITY_RUNTIME_20260929_195051/manifest.json`
3. Respond `CONFIRM` only after each real observation. The collector performs one target enumeration, seven identity reads, then the fixed five network reads per phase. The identity gate must pass before network capture.
   Each phase reads `/proc/net/dev`, `/proc/net/route`, `/proc/net/ipv6_route`, `/proc/net/if_inet6`, then zero-argument `netcfg`.
4. Confirm baseline stock state with CarPlay disconnected. Baseline capture follows.
5. At the prompt, **connect normal wired CarPlay**. Confirm center display, audio, and cluster are normal. Connected capture follows.
6. At the prompt, **disconnect normal CarPlay**. Confirm stock center, audio, and cluster returned. Post-disconnect capture follows.
7. Confirm final stock center, audio, and cluster sanity. Collector exits.
8. State exactly: **CAR MAY BE TURNED OFF NOW. No further Honda or ADB commands will be used in this milestone.**

**Stop immediately** on no/ambiguous target, identity mismatch, unavailable command, unexpected output, timeout, privilege surprise, stock-state failure, or user abort. No fallback command, reconnect, second target, extra phase, root/su, or retry within this session. Record the bounded partial capture and issue the CAR-OFF message after collector exit.

After the car is off, run offline analysis with a new private output directory outside Git:

```sh
python3 tools/analyze_43t0d_capture.py \
  --capture ~/CLARITY_43T0D_<timestamp> \
  --40e-capture ~/CLARITY_RUNTIME_20260929_195051 \
  --output ~/CLARITY_43T0D_ANALYSIS_<timestamp> \
  --private-binding-detail
```

Review the sanitized JSON and Markdown there before copying any sanitized result into Git. `PRIVATE_BINDING_DETAIL.json` remains outside Git. A failed validator produces no derived output. The report generator cannot independently verify the operator's final stock sanity or CAR-OFF statement; record those from the live session.
