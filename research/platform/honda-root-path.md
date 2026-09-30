# Honda existing privilege path — Step 40E3

## Decision

`/system/xbin/su` is a third-party Chainfire SuperSU-family ARM binary and the known `su -c` syntax worked in prior read-only sessions. It is present with the same bytes and mode in the September 18 system archive and the September 25 complete system archive. HondaHack 7.7.7's static code invokes `su` through its embedded libsuperuser path and installs persistent system changes. The binary's original installer and the reason for its `06777` mode are still unknown.

**A safe, zero-target-write elevated read path is NOT established. Do not enable the prepared privileged collector or return to the vehicle for Step 40F.** The archived binary has world/group write bits; its exact live fingerprint and mount state are unknown. Static evidence shows that SuperSU can keep command/log/request/daemon state, while the separate HondaHack root runner explicitly deletes SuperSU logs. No guarantee exists that a direct `su -c` invocation is side-effect free.

## Exact Honda evidence

The archive member `system/xbin/su` is 75,348 bytes, SHA-256 `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`, owner/group `0:0`, mode `06777` (`-rwsrwsrwx`). The exact bytes and metadata agree across:

| Acquisition | Archive SHA-256 | `su` member |
|---|---|---|
| September 18 analysis archive `system-vendor.tar` | `74f61a07df79fe6e1e63c938b7799b9e1638090ab1e350859391101465b212c9` | Exact hash, size, owner and mode match |
| September 18 sealed backup copy | `74f61a07df79fe6e1e63c938b7799b9e1638090ab1e350859391101465b212c9` | Exact hash, size, owner and mode match |
| September 25 complete forensic `filesystems/system.tar` | `74f61a07df79fe6e1e63c938b7799b9e1638090ab1e350859391101465b212c9` | Exact hash, size, owner and mode match |

The September 25 `filesystems/system-vendor.tar` is only `/system/vendor`; its omission of `/system/xbin/su` is expected and says nothing about the binary. The later complete `/system` tar independently preserves the file. Acquisition checksums for the September 18 sealed backup and September 25 forensic bundle validate the archive bytes. These are repeated snapshots of the modified head unit, not a factory-ROM baseline.

The file is ELF32 little-endian ARM EABI5, dynamically linked through `/system/bin/linker`, with NEEDED libraries `libdl.so`, `libstdc++.so`, `libm.so`, and `libc.so`. The ELF contains the marker `2.77:SUPERSU`, the Chainfire copyright string, compiler markers GCC 4.8/4.9, and a help string for `-c, --command COMMAND`. `file`/`objdump` identify ARM; `nm -D` shows UID/GID/group/capability, process, signal, filesystem, mount, socket, and IPC imports. These imports demonstrate available operations, not the operations taken by one specific invocation.

The binary help strings expose `-c`/`--command`, context, login, mount-master/namespace, preserve-environment, shell, version, daemon/reload, install/uninstall, and parent-PID identification options. Environment-related strings include `HOME`, `SHELL`, `USER`, `LOGNAME`, `PATH`, `LD_LIBRARY_PATH`, `ANDROID_PROPERTY_WORKSPACE`, and the preserve-environment option. Imports include `setuid`, `setresuid`, `setreuid`, `setgid`, `setresgid`, `setregid`, `setgroups`, and `capget`; `fork`/`exec*`, `waitpid`, `sigaction`, `kill`, `pthread_kill`, and `raise` are also present. The proprietary stripped control flow has not been completely reconstructed, so exact privilege drop/raise order, environment filtering, signal forwarding, daemon startup, and `-c` side effects remain unknown.

String references include SuperSU config, request, log, and connection paths under `/data/data/eu.chainfire.supersu`; daemon/helper names; `install-recovery.sh`; `su.d`; `chmod`, `chown`, `mount`, and remount command text. Those are implementation fingerprints, not proof that each path is used by every `su -c` call. In the archived filesystem, `daemonsu`, `supolicy`, `sugote`, a SuperSU APK, and `/data/data/eu.chainfire.supersu` are not present in the inspected archives. Historical `su -c id` success is recorded separately and remains valid; the missing companion artifacts make the exact active setup less clear.

Mode `06777` is anomalous within this archive: other special-permission binaries are primarily owner-root `04750`/`06750`, and none has the same group/other write permissions. The mode is preserved in both dated system acquisitions, so it was present by September 18 and remained through September 25. No source inspected here sets `/system/xbin/su` to `06777`. **The exact actor, date, and command that set these bits are UNKNOWN.** The evidence supports “third-party SuperSU installed on the unit before September 18,” not “factory-intentional Honda setting” and not “HondaHack set this mode.”

## HondaHack path and persistent changes

The local installed HondaHack APK is version `7.7.7`, package `cn.autohack.hondahack`, min/target SDK 17, and declares `android.permission.ACCESS_SUPERUSER`. Static DEX analysis found:

- `cn.autohack.hondahack.fc` invokes the embedded `Le/a/a/d` shell library with executable name `su` and a list of commands. Its constructor prepends `rm -rf /data/data/eu.chainfire.supersu/logs/* > /dev/null 2>&1` to each command batch. This is a target-side log deletion, not a read-only action.
- `cn.autohack.hondahack.na.c` assembles persistent operations including `setprop persist.service.adb.enable 1`, `setprop persist.adb.tcp.port 5555`, remounting `/system` read-write, app-process/Xposed setup, and root-startup script installation. This is HondaHack's root-assisted modification flow; it is not safe to reuse for Step 40E/40F.
- `cn.autohack.hondahack.ub.b(Context)` includes a cleanup/block path containing `rm /system/xbin/su`. No inspected path changes the `su` mode to `06777`.
- APK resource `res/raw/install_recovery2_mitsubishi.sh` and archived `/system/etc/install-recovery2.sh` are byte-identical (SHA-256 `1ab539b1023a1a3138c6cebae6fb3ff401a6b18c9fa0769ad4db3fb00fe8292a`). The archived file is root-owned, group 2000, mode `0755`. The init service runs `/system/etc/install-recovery.sh`, which starts `install-recovery2.sh`; that script logs to `/data/local/tmp/log`, polls USB mounts, and if a `recovery.sh` is present copies and executes it as root. This persistent root startup path is not part of the Step 40F collector and must not be used.

These matching HondaHack payloads and static callsites strongly establish that HondaHack used the existing SuperSU `su` path and installed persistent system changes. They do not identify who first placed the `su` binary or set its mode. The separate root startup script is hazardous and unnecessary for the planned maps/smaps read.

## External comparison, not Honda proof

Chainfire's official v2.77 release page dates the release to 2016-08-27 and links its flashable archive. Its official How-To documents the SuperSU daemon/install paths, optional full command-content logging, and that `-c` expects the command as one parameter. These materials are consistent with the local version/help strings but are not a binary hash match: the historical download endpoint returned an HTML landing page, so an upstream ARM binary comparison could not be completed. See [Chainfire v2.77 release](https://chainfire.eu/articles/950/SuperSU_v2.77_BETA_-_Note7_Exynos_shenanigans) and [Chainfire How-To SU](https://su.chainfire.eu/).

The official documentation confirms that SuperSU's design can include daemon startup and optional command logging; it does not tell us this unit's logging setting or whether this specific invocation writes durable data. Therefore:

| Question | Finding |
|---|---|
| Existing mechanism | SuperSU-family `/system/xbin/su`, `-c` accepted historically |
| HondaHack uses it | YES; APK command runner uses `su` through embedded libsuperuser |
| HondaHack persistent changes | YES; static installer and matching root-startup payload |
| `su` mode in dated captures | `06777` in all three full-system copies |
| HondaHack set `su` to `06777` | NOT PROVEN; inspected code contains removal, not this chmod |
| `su -c` guarantees no persistent write | UNKNOWN / NOT SAFE TO ASSUME |
| Step 40F vehicle capture | NOT READY |
