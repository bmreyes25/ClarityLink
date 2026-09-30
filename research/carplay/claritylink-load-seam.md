# ClarityLink jmcs load seam — Step 41C

> **Superseded by Steps 41F/41G:** the init service-scoped `setenv` mechanism is identified, but Honda linker behavior is not confirmed. Do not interpret this historical Step 41C design note as approval or proof that LD_PRELOAD works. Current status is UNKNOWN/parked; see [Step 41G](../../step-reports/41g-offline-linker-behavior-lab.md).

**Historical Step 41C conclusion:** a service environment was identified as a possible loading mechanism; no file was changed in that milestone.

## Historical evidence status (superseded assessment)

- **HONDA CONFIRMED:** the exact boot ramdisk service is `service jmcs /system/bin/jmcs`, class main, root:root. No current `LD_PRELOAD` is set. The global `on boot` environment exports `LD_LIBRARY_PATH=/vendor/lib:/system/lib`.
- **HONDA CONFIRMED:** archived `/init` contains the `setenv` option parser diagnostic. The service stanza can receive an option scoped only to jmcs.
- **AOSP TAG CONFIRMED (comparator only):** Android 4.2.2 init and Bionic source describe service `setenv`, preload handling, and absolute-path handling. These are not Honda facts. See links above.
- **HONDA CONFIRMED:** archived Honda linker hash `608af427ac43a316471e5adc18e25f6d3c9ac5e4ec2c04f19561ee774357aa90` contains `LD_PRELOAD` and `LD_LIBRARY_PATH` strings/pointers; Honda API17 `libdl.so` exports match the AOSP ARM table. Honda exact preload behavior remains unproven after Step 41G.
- **HONDA CONFIRMED:** jmcs is ARM32/EABI5 and its executable mode is 0755, not setuid/setgid. The init service runs as root:root, so ordinary real/effective UID/GID mismatch should not activate secure-execution filtering.
- **UNKNOWN:** Honda `AT_SECURE` check/suppression, absolute path, separator parsing, fatal load behavior, and constructor order. The archive has no policy/file-context database establishing the effective jmcs domain. `AT_SECURE=0` remains an ordinary root-to-root inference, not a Honda observation.

## Candidate staging location (not proven executable-mappable)

**HONDA CONFIRMED:** boot init creates `/data/local/tmp` as mode `0771`, owner/group `shell:shell`; a historical mount snapshot records `/data` rw without `noexec`. It is a staging candidate only. Root DAC traversal/read is plausible, but SELinux access and executable mapping are UNKNOWN. The init file explicitly says this directory should remain empty for security. This is not a deployment instruction.

Because the archived global `LD_LIBRARY_PATH` omits `/data/local/tmp`, an absolute preload pathname would be needed if Honda's linker is proven to accept it. No library was created or deployed.

## Minimum future bounded change

If later validated, the candidate configuration edit is one service-scoped `setenv LD_PRELOAD` line in boot ramdisk `/init.vcm30t30.rc`, plus a separately audited library artifact. This would be a persistent system change requiring its own explicit deployment, backup, boot-recovery, and rollback milestone. Current Honda linker behavior is UNKNOWN; no-op load readiness remains **NO**.
