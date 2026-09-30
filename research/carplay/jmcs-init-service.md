# Honda jmcs init service

**HONDA CONFIRMED — source recovered.** The service is in the Android boot ramdisk file `/init.vcm30t30.rc`, present in both preserved `boot.img` and `root-startup.tar`.

- `boot.img` SHA-256: `37d928201d8861e3037c3e9be8254617eeadfe09e018e37a46500d0711d875cc`.
- `root-startup.tar` SHA-256: `665096f2d25621b0f63b9ae4ecd74a72ce73d736b3486c43042da317683b5817`.
- `init.vcm30t30.rc` SHA-256 inside boot ramdisk: `ce3f9939896d68e1343a701c617f5387374caebf6de9ad2ac636055128a05f51`; the extracted root-startup copy matches byte-for-byte.
- `init.rc` SHA-256: `10c3e65db510593ec353d991bd9777a4ca10fb2ec5eac327dc08df33edccb787`.

Exact complete service stanza:

```rc
#MediaCore
service jmcs /system/bin/jmcs
    class main
    user root
    group root
```

There are no service arguments, `disabled`, `oneshot`, `critical`, `setenv`, socket, capabilities, `seclabel`, or `onrestart` directives in this stanza. No extra supplementary groups are named. The executable is `/system/bin/jmcs`, mode 0755 root-owned in the archived system/vendor filesystem; it has no setuid/setgid mode bits.

## Import closure

The boot ramdisk `init.rc` imports:

1. `/init.usb.rc`
2. `/init.${ro.hardware}.rc` — archived `properties.txt` records `ro.hardware=vcm30t30`, resolving to `/init.vcm30t30.rc`
3. `/init.trace.rc`

`init.vcm30t30.rc` additionally imports `init.nv_dev_board.usb.rc` and `init.tf.rc`. None of those imports another rc file. All six files are present in the 28-entry boot CPIO. Recovery's ramdisk has 76 entries and no `jmcs` stanza.

The `init.vcm30t30.rc` contents inside `boot.img` have the same SHA-256 as the service file in `root-startup.tar`. Other preserved tar archives were enumerated; none besides root-startup contains init rc files. `system-vendor.tar` contains the executable and linker libraries, but no init service declaration.

## Startup semantics

`init.rc`'s `on boot` action starts `class main` (and `core`), so jmcs is automatically started with that class; it is not `disabled`. `oneshot` is absent, so Android 4.2.2 init's documented default restart behavior applies if it exits. No `critical` restart threshold or service-specific `onrestart` action is declared.

The same `on boot` action exports `PATH=/sbin:/vendor/bin:/system/sbin:/system/bin:/system/xbin` and `LD_LIBRARY_PATH=/vendor/lib:/system/lib`. No imported rc sets `LD_PRELOAD`. Init vcm30t30's `on fs` action mounts the APP/CAC/UDA filesystems before `on boot` starts class main.

**AOSP TAG CONFIRMED:** Android 4.2.2 init service grammar supports `setenv <name> <value>` per service, and defines `oneshot` as the option that suppresses restart. [AOSP android-4.2.2_r1.2 init grammar](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/init/readme.txt). The archived Honda `/init` binary (SHA-256 `db46c99b79e7f8ca7bafdb6f9017296272cd56a20be6f2d0deb9e4869ddb5c48`) contains the diagnostic string `setenv option requires name and value arguments`, as well as import parser diagnostics: Honda supports this option.
