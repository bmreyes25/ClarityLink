# ClarityLink jmcs load seam — Step 41C

**Decision: exact service environment seam identified, not deployed.** Add one per-service `setenv LD_PRELOAD <absolute-library-path>` option to the recovered `service jmcs` stanza in `/init.vcm30t30.rc`; stage only a future audited 32-bit ARM EABI library at an absolute path already readable to the root service. This changes neither jmcs nor its stock DT_NEEDED graph. No file was changed in this milestone.

## Why it is technically supported

- **HONDA CONFIRMED:** the exact boot ramdisk service is `service jmcs /system/bin/jmcs`, class main, root:root. No current `LD_PRELOAD` is set. The global `on boot` environment exports `LD_LIBRARY_PATH=/vendor/lib:/system/lib`.
- **HONDA CONFIRMED:** archived `/init` contains the `setenv` option parser diagnostic. The service stanza can receive an option scoped only to jmcs.
- **AOSP TAG CONFIRMED:** Android 4.2.2 init `setenv` sets an environment variable for the launched process. The tagged Bionic linker recognizes `LD_PRELOAD`, loads preloads during executable startup, and uses them before ordinary executable dependency initialization. `LD_PRELOAD` accepts absolute pathnames through `find_library`'s absolute-path branch. [AOSP init grammar](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/init/readme.txt), [AOSP 4.2 linker](https://android.googlesource.com/platform/bionic/+/android-4.2_r1/linker/linker.cpp).
- **HONDA HIGH CONFIDENCE:** archived Honda linker hash `608af427ac43a316471e5adc18e25f6d3c9ac5e4ec2c04f19561ee774357aa90` contains `LD_PRELOAD` and `LD_LIBRARY_PATH`; Honda API17 `libdl.so` exports match the AOSP ARM table. Honda exact preload control flow was not disassembled in this milestone.
- **HONDA CONFIRMED:** jmcs is ARM32/EABI5 and its executable mode is 0755, not setuid/setgid. The init service runs as root:root, so ordinary real/effective UID/GID mismatch should not activate secure-execution filtering.
- **UNKNOWN:** kernel `AT_SECURE` result for this service. Android's linker suppresses `LD_PRELOAD` in secure execution; a SELinux domain transition can affect that status. The archive has no policy/file-context database establishing the effective jmcs domain. Therefore actual Honda honor remains HIGH-CONFIDENCE, conditional on `AT_SECURE` being false.

## Narrowest theoretical staging location

**HONDA CONFIRMED:** boot init creates `/data/local/tmp` as mode `0771`, owner/group `shell:shell`; historical mounts show `/data` as persistent read/write and not `noexec`. It is the narrowest existing shell-managed staging directory identified; the root jmcs service can pass ordinary DAC read/execute checks for a file placed there. The init file itself says this directory should remain empty for security. SELinux access to a staged library is UNKNOWN, and reboot cleanup/persistence is not guaranteed by current evidence. This is an analysis of existing configuration, not a deployment instruction.

Because the archived global `LD_LIBRARY_PATH` omits `/data/local/tmp`, any future use should be an absolute preload pathname. No library was created or deployed.

## Minimum future bounded change

The minimum configuration edit is one service-scoped `setenv LD_PRELOAD` line in the boot ramdisk's `/init.vcm30t30.rc`, plus the separate audited library artifact. This does modify the boot ramdisk and is a persistent system change requiring its own explicit deployment, backup, boot-recovery, and rollback milestone. No update to `/system/bin/jmcs`, `libcarplay_proxy.so`, or Type111 is required for the loading seam itself. Live deployment readiness remains **NO** until secure-exec/SELinux access, compatibility gates, and recovery are established.
