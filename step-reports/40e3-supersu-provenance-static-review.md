# Step 40E3 — SuperSU provenance, integrity, and side-effect review

**Status: OFFLINE REVIEW COMPLETE; no privileged live read is approved.** The vehicle was not accessed, ADB was not used, and no firmware, target, or HondaHack file was changed. The `/system/xbin/su` binary was treated as data and never executed.

## Decision

The archived binary is a third-party Chainfire SuperSU-family `su`, marked `2.77:SUPERSU`; it is not supported as a factory Honda binary by the available evidence. The exact bytes and mode `06777` appear in the September 18 system archive and the September 25 complete system archive. HondaHack 7.7.7 uses this `su` route and its app contains persistent root operations. The inspected HondaHack code does **not** show a chmod of `/system/xbin/su` to `06777`; attribution for that exact permission remains unresolved.

The Step 40E2 fixed-operation collector remains disabled for live use. The binary's mode is not acceptable for a setuid-root file, its live fingerprint is unknown, and neither static evidence nor the historical successful `su -c id` proves that the proposed invocation leaves no persistent state. In particular, command logging/request and daemon paths are present in the binary; Chainfire documents optional command-content logging. Do not start Step 40F.

## Acquisition cross-check

The extracted member is 75,348 bytes, SHA-256 `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`, uid/gid 0:0, mode 06777. The complete archive SHA-256 is `74f61a07df79fe6e1e63c938b7799b9e1638090ab1e350859391101465b212c9` in all these copies:

| Source | Result |
|---|---|
| September 18 working `system-vendor.tar` | Member bytes and tar metadata match |
| September 18 sealed backup `system-vendor.tar` | Archive SHA and member match the working copy |
| September 25 complete forensic `filesystems/system.tar` | Archive SHA and member match the September 18 copies |
| September 25 `filesystems/system-vendor.tar` | Different archive, source is `/system/vendor`; it does not contain `/system/xbin/su` and is not a conflicting observation |

The corresponding September 18 and September 25 acquisition checksum manifests match the archive hashes. The repeated preserved images prove the mode was present at least by September 18 and remained through September 25. They do not prove this was Honda factory state because they are captures from the already modified vehicle, not a stock image baseline.

The binary reports ELF32 ARM EABI5, dynamic interpreter `/system/bin/linker`, NEEDED `libdl.so`, `libstdc++.so`, `libm.so`, `libc.so`, and entry point `0x3528`. Its strings include Chainfire copyright text, `2.77:SUPERSU`, compiler markers GCC 4.8 and 4.9, and option help. This strongly identifies its family/version; it is not an exact upstream binary hash match. The download endpoint linked by Chainfire returned an HTML page, not the archive, so no external binary comparison was made.

## Static behavior inventory

| Topic | Local evidence | What remains unproven |
|---|---|---|
| `-c` parsing | Usage strings say `-c, --command COMMAND` passes a command to the invoked shell; prior read-only records show `su -c id` returning UID 0 | Exact quoting/parser edge cases for this build; whether `su -c` starts a daemon or changes saved state |
| Privilege transitions | Dynamic imports include setuid/setresuid/setreuid, setgid/setresgid/setregid, setgroups, and capget | Exact order, credential/capability set, and parent/child behavior |
| Environment | Help includes `--preserve-environment`; strings include HOME/SHELL/USER/LOGNAME/PATH/LD_LIBRARY_PATH/ANDROID_PROPERTY_WORKSPACE; imports include getenv/setenv/putenv/unsetenv | Exact whitelist, sanitization, and environment passed to the child |
| Signals/processes | Imports include sigaction, kill, pthread_kill, raise, fork, execve/execv, waitpid, setsid, pipes and polling | Which signals are installed/forwarded or which processes are created for this invocation |
| Files and persistence | Imports include open/write/unlink/mkdir/chmod/chown/fchmod/fchown/mount; strings name SuperSU config, requests, logs, connections, daemon and helper paths | Which paths a direct `su -c cat /proc/...` touches; whether any setting makes the action write-free |
| IPC/network | Imports include socket, socketpair, connect, accept, sendmsg/recvmsg, select and poll | Whether the archived installation has a daemon and whether this call contacts it |
| Installation/init | Strings include install/uninstall, daemon/reload, `install-recovery.sh`, `su.d`; archives lack `daemonsu`, `supolicy`, `sugote`, SuperSU APK, and SuperSU app data | Whether a helper is embedded/launched another way; exact installation history |

The presence of an imported function or string is not treated as proof the corresponding path executes for the collector command.

## HondaHack linkage and modification history

The installed HondaHack APK identifies as package `cn.autohack.hondahack`, version 7.7.7, min/target SDK 17, and declares `ACCESS_SUPERUSER`. Its DEX static references establish:

1. `cn.autohack.hondahack.fc` invokes the embedded `Le/a/a/d` shell API using executable name `su` and a command list. Its constructor prepends `rm -rf /data/data/eu.chainfire.supersu/logs/* > /dev/null 2>&1`. This is an explicit persistent target-side log deletion.
2. `cn.autohack.hondahack.na.c` constructs commands to persistently enable ADB properties, remount `/system` read-write, set up Xposed/app_process files, and install/maintain the root startup script.
3. `cn.autohack.hondahack.ub.b(Context)` contains a cleanup/block command `rm /system/xbin/su`. The inspected methods contain no `chmod 06777 /system/xbin/su` or equivalent permission setter.
4. The APK's `res/raw/install_recovery2_mitsubishi.sh` is byte-identical to archived `/system/etc/install-recovery2.sh`, SHA-256 `1ab539b1023a1a3138c6cebae6fb3ff401a6b18c9fa0769ad4db3fb00fe8292a`. The archived member is mode 0755, root:gid 2000. `init.rc` starts `/system/etc/install-recovery.sh`, which starts that script. It writes `/data/local/tmp/log`, polls USB mount points, copies `recovery.sh`, and executes the USB-supplied script as root.

This is strong evidence HondaHack installed/maintained persistent root and Xposed changes using the existing `su` facility. It does not prove that HondaHack originally installed the SuperSU binary or set its `06777` mode. The USB recovery hook is not a safe substitute privilege path and is explicitly excluded from the prepared collector.

## External comparison (not Honda proof)

Chainfire's official v2.77 post identifies the release as a 2016-08-27 SuperSU beta and links the flashable ZIP. The official How-To describes SuperSU daemon installation paths, optional logging of command content, and the single-parameter `-c` contract. These facts are consistent with local marker/help strings, but no external ARM binary was acquired for a hash match. References: [Chainfire v2.77 release](https://chainfire.eu/articles/950/SuperSU_v2.77_BETA_-_Note7_Exynos_shenanigans), [Chainfire How-To SU](https://su.chainfire.eu/).

## ECC and Step 40F gate

ECC security-review workflow was applied to privilege boundaries, command dispatch, state mutation, logs, root startup, data privacy, and evidence provenance. An independent ECC reviewer is unavailable in this session; no independent review is claimed. The requested second-Codex review of a Step 40F procedure has not been performed.

**PERSISTENT CONFIG CHANGE REQUIRED TO INVOKE EXISTING `su`:** NO, no new install/chmod/service/config operation is required merely to invoke the existing executable.

**INVOCATION GUARANTEED TO MAKE ZERO PERSISTENT WRITES:** NO / UNKNOWN.

**STEP 40F:** NOT READY. Do not use ADB, execute `su`, or run the USB recovery hook for this milestone. The next permitted work is further offline provenance/behavior analysis or an independent review after a separately bounded Step 40F procedure exists.
