# STEP 43T0-DPREP — OFFLINE LIVE-CAPTURE ANALYSIS PIPELINE

Starting requested baseline: `b3451ca3850e537fc32e42105fbbc4977228646c`. Actual clean starting HEAD: `ee35c9f3727dbff6979dc25cc8c77d9ffb721643`, a descendant recording the separately attempted 43T0-D fail-closed host enumeration. This prep made **no Honda contact, no ADB use, and zero target writes**. No collector execution occurred.

## Contract and implementation

The analyzer pins D0 collector version, source hash, approved-plan commit, 23-command order, exact prefix rule, result classes, byte counts, SHA-256, target reference redaction, and identity fingerprints. It rejects unexpected files, symlinks, oversize input, tampering, and network reads without matched identity. Partial captures are bounded. The five parsers cover `/proc/net/dev`, IPv4 route, IPv6 route, IPv6 addresses, and the D0 zero-argument toolbox-style `ifconfig` output. Unknown `ifconfig` syntax fails as `UNEXPECTED_FORMAT`.

IPv6 route field provenance: [Linux v3.1 `net/ipv6/route.c`, `rt6_info_route`](https://github.com/torvalds/linux/blob/v3.1/net/ipv6/route.c#L2625-L2648) emits destination/prefix, source/prefix, next-hop neighbor key, metric, reference count, use count, flags, device name. The parser follows that serialization and does not infer unprinted semantics. The collector format gate requires the same 10 fields.

The delta engine records interface/address/route changes and phase reversal without arbitrary scores. The 40E adapter uses only the sanitized, verified [43T0-A evidence](43t0a-40e-network-evidence-reanalysis.md): stock-CarPlay-correlated IPv6 link-local **global socket** rows. It never promotes process ownership or listener reachability. Supplying the private 40E bundle verifies its pinned manifest checksum read-only; the adapter does not copy raw rows.

Public JSON and Markdown redact exact addresses. Optional `PRIVATE_BINDING_DETAIL.json` is created only outside Git at mode 0600. No raw capture is copied or changed. G11-E remains `NO / READ_BLOCKED_WITHOUT_PRIVILEGE`; G11-F remains `NO`; `HONDA_CONFIRMED_TYPE111` is never emitted. Strong A-D findings recommend only offline 43T1-PREP; incomplete/contradictory evidence returns to ECC or NO-GO.

## ECC security and evidence review

Applied ECC security-review input validation, bounds, path and symlink rejection, provenance checks, privacy scan, no sensitive errors, and fail-closed output ordering. The code has no subprocess, socket, ADB connection, or network execution path. Evidence classifications separate Honda read-only observation, 40E runtime timing correlation, inferred policy, and privilege-blocked ownership. A global socket row is not `jmcs` ownership. This is an ECC-method self-review, not an independent ECC approval.

The previous live attempt left an ADB connection precondition unresolved. The [one-page runbook](../research/runtime/43t0d-live-runbook.md) requires its separate offline review before any future live retry. This prep does not replace or begin 43T0-D.

## Verification

Synthetic parser and scenario tests, malformed/truncation tests, validator prefix/command/integrity tests, source immutability, path safety, privacy, report generation, and G11-F invariant are in `tests/tools/test_step43t0d_prep.py`. The committed [synthetic JSON example](../research/runtime/43t0d-synthetic-example.json) is explicitly labeled synthetic and contains no raw capture. Focused suite: 40 passed. Configured offline suite: 500 passed, 3 skipped (plus smoke and simulator checks). `git diff --check` and edited Markdown link validation passed. Hosted CI remains to be checked after push.
