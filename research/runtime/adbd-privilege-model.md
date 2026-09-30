# Honda API 17 `adbd` privilege model (Step 40E4)

## Scope and decision

This is an offline review of archived filesystem members and prior recorded shell identity. No ADB command was run in this review; no archived executable was run. The examined image is the preserved, already-modified head-unit capture, not a pristine factory image.

**Finding:** the archived configuration does not establish a zero-change way for `adbd` to provide UID 0. It explicitly sets `ro.secure=1` and `ro.debuggable=0`; the build is `user` / `release-keys`; init starts `adbd` as a disabled service under the `adbd` SELinux label when USB configuration requests ADB. The actual previously recorded interactive shell identity is UID 2000 (`shell`), not root. Do not use `adb root` or change properties/USB configuration as a workaround.

## Archive evidence

Primary sources are members read from `/Users/bmreyes24/ClarityLab/clarity-analysis/root-startup.tar` and `system-vendor.tar` with `tar -xOf` and `tar -tvf`:

| Member | Honda archive evidence | Assessment |
|---|---|---|
| `default.prop` (root-startup archive) | `ro.secure=1`, `ro.debuggable=0`, `persist.sys.usb.config=mtp` | Default archived properties are production-like; the `mtp` default does not start ADB. |
| `init.rc` | `service adbd /sbin/adbd`, class core, socket `adbd` mode `660 system system`, `disabled`, `seclabel u:r:adbd:s0`; starts on `ro.kernel.qemu=1` only as an emulator trigger | `adbd` is not declared as a root service. The service user is implicit in Android init defaults; no `user root` override appears. The socket is for the ADB transport, not a root command proxy. |
| `init.usb.rc` | Configurations containing `adb` start `adbd`; `persist.sys.usb.config=*` copies the persistent property to `sys.usb.config` | This is an init-controlled USB-function transition. It writes USB sysfs state and changes runtime properties. It is not a read-only privilege route. |
| `system/build.prop` | `ro.build.type=user`, `ro.build.tags=release-keys`, SDK 17, Android 4.2.2 | Supports production build identification, not a special engineering root state. |
| `sbin/adbd` | 157,572-byte ELF32 little-endian ARM EABI5, static, stripped, from `root-startup.tar` | Binary identity is confirmed. Stripped strings did not yield a useful policy/privilege trace; no binary execution or disassembly was performed. |

The archives also contain HondaHack code described in [the existing root-path report](../platform/honda-root-path.md), which sets persistent ADB-related properties as part of its modification flow. That establishes the availability of a *modifying* path in HondaHack, not that the present property state can be safely changed or that `adbd` would then become root. Prior manual ADB evidence records `uid=2000(shell)`. It is consistent with this model and rules out “the current ADB shell is already root.”

## Distinct mechanisms

| Mechanism | What the evidence supports | Step 40E4 disposition |
|---|---|---|
| `adb shell` | ADB shell process recorded as UID 2000. | Useful for its already-readable files only; live procfs evidence already showed permission denial for `jmcs` maps/smaps/fd. |
| `adb root` | No archived property or init rule establishes that a root adbd transition is enabled. `ro.secure=1`, `ro.debuggable=0`, `user` build are contrary indicators. | **Not a candidate.** Do not try it. No claim is made that the exact stripped adbd error response was recovered. |
| HondaHack ADB enablement | Static HondaHack command construction sets persistent ADB properties and remounts `/system` read-write. | **Disallowed.** It changes persistent configuration and is outside a zero-write procedure. |
| Shell invoking `/system/xbin/su` | Separate SuperSU route, already assessed in Step 40E3. | Not part of `adbd`; zero-write behavior remains unproven. |
| Root-owned init service | Separate process launched by init; some have shell-accessible sockets or diagnostic operations. | See [alternative root paths](alternative-root-paths.md). None is an approved `adbd` root mechanism. |

## Decision

**ADBD CAN PROVIDE ROOT WITHOUT SU: NO, on the evidence available for the archived configured system.** The archive supports “not enabled by the checked production defaults,” not a universal theorem about every possible boot-time mutation or patched adbd. Changing `ro.secure`, `ro.debuggable`, `persist.service.adb.enable`, USB functions, or init state would be a state-changing experiment and is not authorized by the Step 40E4 offline audit.

**Useful direct unprivileged reads:** yes, but they do not include the denied `/proc/<jmcs>/maps`, `smaps`, and `fd` files observed in the prior live capture. They may still cover identity, public properties, system-wide proc network tables, and other paths whose permissions allow UID 2000. Exact data and access should be taken from the already captured Step 40E bundle, not inferred from this archive review.

## Evidence limits

- No pristine factory image is available here; the archive reflects a unit with HondaHack modifications.
- Current live properties/process credentials may differ from archived defaults. The historical shell UID is evidence for that session only.
- `adbd` is stripped. This review did not reconstruct its internal root-mode decision branch.
- No attempt was made to start/restart `adbd`, use `adb root`, alter properties, or inspect the vehicle.
