# Step 41C — recover Honda jmcs init service and load environment

**Result: service stanza recovered; scoped preload path is technically available; no deployment.** Offline only. No vehicle, ADB, firmware modification, library staging, preload experiment, jmcs patch, or Type111 work.

## Archive recovery and cross-check

The service declaration resides in `/init.vcm30t30.rc` in `root-startup.tar`; the Android boot image `boot.img` independently contains a 28-file gzip CPIO ramdisk with the same `/init.vcm30t30.rc` bytes. The file SHA-256 is `ce3f9939896d68e1343a701c617f5387374caebf6de9ad2ac636055128a05f51`. The image's recorded SHA-256 is `37d928201d8861e3037c3e9be8254617eeadfe09e018e37a46500d0711d875cc`; root-startup tar SHA-256 is `665096f2d25621b0f63b9ae4ecd74a72ce73d736b3486c43042da317683b5817`. The `recovery.img` ramdisk was also parsed and has no jmcs service. Tar manifests for preserved archives were searched; the system/vendor tar contains `system/bin/jmcs` and linker files but no init rc.

Boot init imports `init.usb.rc`, `init.${ro.hardware}.rc`, and `init.trace.rc`; exact archived property `ro.hardware=vcm30t30` resolves the platform import to `init.vcm30t30.rc`. That board file imports `init.nv_dev_board.usb.rc` and `init.tf.rc`; neither imports additional rc files. All imported files occur in the boot CPIO. No extra import was omitted from the launch chain.

The complete service stanza is:

```rc
service jmcs /system/bin/jmcs
    class main
    user root
    group root
```

Arguments and additional options are absent. There are no `disabled`, `oneshot`, `critical`, `setenv`, socket, capabilities, `seclabel`, or `onrestart` lines. Main class starts on the normal `on boot` path; no `oneshot` means init's default restart-on-exit behavior. A system-wide `LD_LIBRARY_PATH=/vendor/lib:/system/lib` is exported during boot, but no `LD_PRELOAD` is present.

## Load feasibility

Android 4.2.2 init documents service-level `setenv`; the archived Honda `/init` binary contains the `setenv option requires name and value arguments` parser diagnostic. A future service-scoped variable can therefore be supplied without editing jmcs. The Honda linker advertises `LD_PRELOAD` and its architecture/export fingerprint matches API17 Bionic. Honda jmcs is ARM32 EABI5, mode 0755, and service credentials are root:root, so ordinary setuid/setgid secure-mode filtering is not expected. However, the archived SELinux policy/file-context mapping is absent; if its execution transition sets `AT_SECURE`, Honda's linker will ignore `LD_PRELOAD`. Thus **LD_PRELOAD HONORED BY HONDA LINKER: HIGH-CONFIDENCE, conditional on AT_SECURE=false**.

The boot init creates `/data/local/tmp` mode 0771 shell:shell, and historical mount evidence has `/data` read/write without `noexec`. This is the narrowest existing shell-managed candidate staging location; exact SELinux read/mmap permission and cleanup/persistence are unresolved. The init source explicitly cautions that the directory should remain empty. No path was used.

## Decision gate

```text
JMCS SERVICE FOUND: YES
SERVICE FILE: boot.img ramdisk /init.vcm30t30.rc (matching copy in root-startup.tar)
JMCS EXECUTABLE: /system/bin/jmcs
SERVICE USER/GROUP: root / root (no extra groups)
SETENV SUPPORTED HERE: YES (Honda init binary parser evidence and Android 4.2.2 grammar)
LD_PRELOAD HONORED BY HONDA LINKER: HIGH-CONFIDENCE; subject to AT_SECURE/SELinux condition
EXACT FUTURE LOAD SEAM IDENTIFIED: YES (one service-scoped setenv option plus absolute library path)
LIVE DEPLOYMENT READY: NO
BIGGEST BLOCKER: preserved image omits SELinux policy/file contexts needed to establish whether jmcs exec is AT_SECURE and whether jmcs may map a library from /data/local/tmp
```

## Verification

Offline checks included tar member enumeration, Android boot-image ramdisk parsing, CPIO member enumeration, exact SHA-256 comparison of boot CPIO and root-startup service file, import-closure tracing, and archive-wide init rc name search. No code tests were relevant to this documentation-only recovery. `git diff --check` is run after edits.
