# CL-HONDA-COMPREHENSIVE-READINESS-20261030 runbook

This is an integrated eligibility and operator guide, not a combined authorization. `safeForHonda() == false` and `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` remain in force. A stage is executable only after its own profile, exact review records, owner decision, private output root, target identity, and physical baseline pass. A later stage never follows automatically from an earlier one.

## Common baseline

Use a new owner-only directory outside the repository, mode `0700`; capture files and review records are mode `0600`. Do not put serials, endpoints, raw `/proc` output, reviewer identity, photos, or credentials in Git. Be outdoors, stationary in Park, parking brake set, owner present, with normal center display, cluster, Navigation, audio, and no unexpected warning. For C-P, use ON with the brake pedal not pressed and READY absent. If that state does not support the reviewed activity, stop: do not move to READY, root, another ADB endpoint, or a different procedure. EV-only expectations do not guarantee that the engine cannot start when READY is present.

At every stop: preserve host evidence, assess normal factory behavior with the owner, record the failed phase and observed condition, and end the session. Do not retry, substitute a command, escalate privilege, or continue to another stage.

## Stage P — passive C-P

**Eligibility:** The C-P policy amendment must be adopted on protected `main`; the current main checkout must pass pinned profile/source checks; Codex and Claude must supply exact-source AI engineering records; ECC is optional only when unavailable; record a truthful reason and `no_completed_review_withheld: true`. The owner attests that no completed or received ECC report is withheld; any such report must be included and validated. This is an owner attestation, not an independently enforceable control: the validator cannot inspect external services or independently prove availability or truthfulness. Ben Reyes must separately confirm the fresh nonce-bound prompt for each invocation. The nonce is per invocation and does not persistently consume the approval file; after a stop or interruption, do not relaunch until the cause is resolved and Ben Reyes makes a new explicit decision. This is operator discipline, not a technical replay guard. Interruption during the final owner prompt stops before capture creation, so no capture directory or failure card is created. This is owner-assumed risk, not human certification. HondaHack and root remain excluded.

**Entry point:**

```sh
python3 tools/honda-readonly-preflight/campaign_runner.py dry-run
python3 tools/honda-readonly-preflight/campaign_runner.py run \
  --approval-file /owner-only/reviews/cp-authorization.json \
  --output-root /owner-only/captures
```

The runner itself demands the exact serial from the private authorization. It never auto-selects a device for the live path. The profile contains eight phases and 135 fixed commands. Each command is at most 20 seconds and 4 MiB; aggregate ceilings are 2,425 seconds and 158,400,512 bytes, excluding owner transition waits. It records normal baseline; exact identity; normal stock CarPlay; Navigation selected, deselected, and reselected; normal disconnect; then final restoration. The owner performs every physical transition and must re-attest before and after collection.

Expected completion is a private manifest, SHA-256 inventory, bounded summaries, and a restoration attestation. An interrupted capture can be checked offline with `campaign_runner.py recover`; recovery never resumes vehicle commands.

## Stages R0–R3 — separately controlled privileged metadata

**Eligibility for all R stages:** PR #119 must be adopted; the exact `CL-HONDA-ROOT-READ-EVIDENCE` profile/source locks must verify; a qualified independent human reviewer with Android/API17 or legacy-ADB privilege and automotive diagnostic competence must approve the exact stage; Ben Reyes must separately authorize the exact stage, serial, power state, and scope. The profile is currently live-disabled.

**R0:** fixed unprivileged `id`, `/proc/version`, five target properties, `sha256sum /system/xbin/su`, and `ls -l /system/xbin/su`. It must match the reviewed SuperSU fingerprint, root ownership, setuid requirement, and no group/other write bits. Archived mode `06777` fails the acceptance rule. Do not execute `su`, repair its mode, change ownership, replace it, or use another privilege mechanism.

**R1:** only `/system/xbin/su -c id`, capped at 5 seconds/16 KiB, after a R1-specific approval that explicitly accepts possible prompt, daemon, request, or log state. The historic SuperSU zero-write path is not established; this stage is therefore not eligible today.

**R2:** one disconnected metadata phase only after R1 passes under its reviewed criteria. The fixed profile obtains `jmcs` process identity before and after, `/proc/<pid>/maps`, optional `smaps`, executable symlink, bounded FD symlinks, and five `/proc/net` tables. It excludes memory, environ, credentials, keys, signals, attachment, helpers, installs, settings, mounts, and arbitrary command strings.

**R3:** matching disconnected/connected/disconnected metadata phases, only after a separate R3 decision. The owner performs ordinary stock CarPlay connection and disconnection. It does not initiate negotiation or change the receiver.

The eventual reviewed entry point is the PR #119 `privileged_campaign.py` controller, not the obsolete `privileged_session.py`. Before any future live use, it must remain mechanically disabled until R0/R1 acceptance is demonstrated and a separately reviewed change enables it. The root review packet is included in [PR #119](https://github.com/bmreyes25/ClarityLink/pull/119).

## Stage H — HondaHack observation

**Eligibility:** PR #119 profile adoption, qualified independent automotive/Honda display-observation review, and a separate owner decision. It is neither a C-P phase nor a root phase.

Use only existing HondaHack UI and ordinary factory Navigation controls: baseline; confirm casting disabled; Start Casting once; observe Navigation selected; deselect; reselect; Stop Casting once; confirm center display, cluster, Navigation, and audio restoration. No ADB, root, APK installation, Xposed change, warning generation, service restart, receiver change, or display-control call is permitted. Stop immediately on abnormal cluster, warning, display, Navigation, or audio behavior. The controlling profile and review packet are in PR #119.

## Stage A — offline analysis

Stage A is allowed only after its source capture is authorized and retained privately. Use `tools/honda-readonly-preflight/analyze.py` against the capture directory; it can analyze interrupted evidence but cannot continue collection. Publish only a reviewed, minimized summary.

Interpretation rules: a process-owned endpoint requires exact `jmcs` FD-symlink inode equality with a parsed `/proc/net` row; static ELF NEEDED entries are not runtime mapping proof; maps/smaps permission denial is unknown, not an empty address space; and absent recognized Type111 markers must be reported exactly as `TYPE111_NOT_OBSERVED_IN_AVAILABLE_LOGS`. It does not prove incompatibility.

## Active instrumentation

No instrumentation stage is defined for vehicle execution. Existing diagnostics, root metadata, temporary helpers, tracing, Frida/ptrace, Xposed, and native patching differ in privilege, process interruption, recovery, and evidence value. Before any future proposal, state one missing datum that passive/authorized metadata cannot answer, target API17/ARMv7 compatibility, installation requirement, cleanup and independent recovery proof, factory Type110 impact, and a distinct qualified review/owner authorization. PR #117 is offline stock-pass-through research only and has a failing API17-navigation check; it is not a vehicle procedure.
