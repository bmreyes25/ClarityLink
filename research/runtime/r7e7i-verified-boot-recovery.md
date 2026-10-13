# R7E7I-RB1 — verified-boot recovery investigation

**Decision: `R7E7I_VERIFIED_BOOT_ROUTE_CONDITIONAL`.** Linux v3.1 upstream does not expose `/proc/sys/kernel/random/boot_id` in `drivers/char/random.c`. Preserved Honda runtime evidence identifies the target kernel as `3.1.10+`; a vendor backport is possible but unproven. Therefore, the route is not presently supported for this Honda and has no review-ready vehicle command package. If an exact, hash-identified Honda kernel source/image establishes a stable per-kernel boot UUID and independent A/B receipt ordering can be arranged, the proof model is technically sound. No Honda observations were made. Honda `boot_id` availability remains **UNKNOWN**; historical termination remains **NOT ESTABLISHED**.

## Starting state and preserved evidence

- Repository/branch: `bmreyes25/ClarityLink`, `architecture/r7e-parked-car-compatibility-preparation`.
- Starting HEAD: `10f0b8b3ad57656dfab336caf537eb35964961fe` (clean, tracking origin). The supplied expected HEAD `a973cd8883624e4f064f30e478de5cec2d54bbe7` was not current.
- PR #19 was open at that same starting HEAD when checked locally. No remote update or merge was performed for this investigation.
- The preserved Test A failure record is present at `build/r7e6a/test-a/evidence/collector-failure-20261012T021444Z-b64f.json`, SHA-256 `21e6551fde4498603dbfc9129aa4f32a61b0f0c7e89f3a70ba5035cfccee430e`. This corrects the prior chronology report's path typo (`r7e6` vs `r7e6a`); the actual bytes match its cited digest.
- The failure record says the push was attempted, the diagnostic started, the version command returned, the process state became uncertain, and cleanup/final absence were not checked. Its UTC field is not used to infer ordering or a time bound.
- Preserved Phase R reviewed receipt SHA-256 `001e13ba7c5911a5d03e10114d6d8925cb3e3fa4c619b2ce2ba396bd1cae3ddd`, with raw receipt SHA-256 `1ef979927dc83401c36da11a6499e23a77c9016f2c9c1487a19013d204652fb8`. It records the exact old file present (7904 bytes, mode 0555, shell:shell, expected MD5), zero executable launches and no cleanup. This is not process-safety evidence.
- Historical command manifest `research/runtime/r7e6-test-a-plan-manifest.json` specifies one explicit push and direct `--version`/`--self-test` invocations. No init service, APK, boot receiver, startup script, persistent property, daemon, or scheduler installation appears in that manifest. The manifest establishes intended scope, not a complete audit of external actors or vendor configuration.
- Preserved Honda platform evidence (`research/platform/honda-kernel-runtime.md`, `honda-kernel-provenance.md`) identifies Linux `3.1.10+`, Android 4.2.2/API17, and an exact kernel-image hash; the actual boot image/kernel binary and exact source/config are not present in this checkout.
- Existing Phase S/Phase C collectors and their manifests were preserved unchanged. Phase S remains `PHASE_S_BLOCKED`; Phase C remains not ready and unauthorized; Test A remains blocked.

## Technical finding

Modern Linux documentation defines `/proc/sys/kernel/random/boot_id` as a UUID stable within one boot. But the period-correct [upstream Linux v3.1 random driver](https://raw.githubusercontent.com/torvalds/linux/v3.1/drivers/char/random.c) contains no `boot_id` interface. The target's preserved runtime report says `3.1.10+`; the exact Honda kernel source/config is unavailable and its image is outside this checkout. Any support would require an evidenced vendor backport and confirmation that the exposed value is stable per kernel execution. Until then, the route must be treated as unavailable for observation planning. AOSP 4.2.2 init supports service definitions, boot actions and properties; its implementation restarts services after exit. A genuine kernel restart ends the old kernel's process table; a userspace/UI restart does not.

The file is under `/data/local/tmp`; a kernel reboot does not itself establish that the file was removed or that the data partition retained it. The Phase R evidence already shows that it remained present at that observation. A boot witness says nothing about current process references, later launches, file identity, cleanup safety, or Test A readiness.

## Proof model

If a vendor backport is later proven offline, Observation A must be captured after the original invocation and Observation B later, on the same independently identified Honda hardware. A and B must each bind the exact ADB serial, hardware identity and build fingerprint to the boot UUID and a signed/hash-bound receipt. An independent witness must verify the sequence and receipt chain; host timestamps are not chronology evidence. A separate independently reviewed causal record must establish that the old invocation occurred before A. If that relation cannot be supported without assuming a historical clock, the boot route remains blocked.

Only valid, different boot UUIDs with all identity, ordering, receipt, capability and review gates can support the narrow historical-termination finding. Identical IDs, malformed/missing IDs, mismatched hardware, ambiguous source, missing receipts, unverified ordering or synthetic evidence fail closed. The host model always reports synthetic inputs as `MODEL_ONLY_*`; its flags and hashes are not signatures and cannot establish real evidence.

## Independent decisions

| Question | RB1 result |
|---|---|
| Historical invocation terminated | Not established; candidate future boot route is conditional |
| Current executable references | Unknown; existing process-evidence parser remains the separate contract |
| Project relaunch persistence | `NO_PROJECT_PERSISTENCE_EVIDENCED` by the reviewed Test A command manifest only |
| External relaunch source | `UNRESOLVED_EXTERNAL_RELAUNCH_PATH` |
| Old file identity/current state | Phase R observed the expected file present then; current state is unknown |
| Phase C cleanup | Not ready; not authorized |
| Phase S | Blocked; old clock-based route unchanged |
| Test A | Blocked |

The old file can be launched again by a future actor even after a reboot. An independently reviewed no-relaunch assessment and complete current-reference evidence remain separate cleanup gates. Neither boot witness nor model output grants authorization.

## Timeout assessment

The previous API17 timeout remains a failed/uncertain historical run; no reclassification is made. Existing bounded host cleanup preserves failure evidence and does not increase the production 12-second watchdog. This RB1 change adds no emulator runner or retry policy; the current timeout conclusion remains “bounded abort path reviewed, root cause unresolved,” and does not establish Test A readiness.

## Validation and boundaries

The new parser/model reads caller-supplied JSON only. It has no ADB dependency or device-facing code. Test fixtures are synthetic and cannot be promoted by setting review flags. No Phase S, Phase C, Test A/B, Honda command, live inspection, cleanup, reboot, APK install, or vehicle/iPhone operation occurred. Exact test results and hosted-check status are recorded in the final task response; final commit and PR status are supplied there.

## Primary technical references

- [Linux kernel `/proc/sys/kernel` documentation](https://www.kernel.org/doc/html/v5.18/admin-guide/sysctl/kernel.html#random): boot ID remains unvarying within one boot.
- [Android 4.2.2 AOSP init implementation](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1/init/init.c): init launches services and contains service restart logic.
- [Android 4.2.2 AOSP init language reference](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/init/readme.txt): actions, imported init configuration, boot trigger, and services.
- [Linux v3.1 random driver](https://raw.githubusercontent.com/torvalds/linux/v3.1/drivers/char/random.c): period-correct upstream comparison; no `boot_id` interface is present.

## ECC review status

**`MANUAL_ECC_GUIDED_REVIEW`**. The ECC security-review and Python-testing guidance informed the fail-closed review. No independent reviewer endpoint or external human reviewer was available during implementation; no independent approval is claimed. Require an independent review of the resulting commit before relying on any future live receipt.
