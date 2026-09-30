# Honda existing privilege path — Step 40E2

## Evidence

An immutable local `system-vendor.tar` contains `system/xbin/su`. Its extracted binary is ELF32 ARM EABI5, shared-object type, dynamically linked, and stripped; SHA-256 is `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`. The preserved tar metadata lists owner/group `0:0` and mode `-rwsrwsrwx` (octal `06777`). Static strings identify the Chainfire SuperSU family (`eu.chainfire.supersu`, `daemonsu`, `supolicy`) and document `-c, --command COMMAND`. The local artifact was inspected as data only; no unknown binary was executed.

The project’s previous read-only sessions recorded successful `adb shell su -c id` results with `uid=0(root)`, and subsequent root-scoped proc/storage reads. This proves that the `su -c` form worked on this unit at those times. `su 0 command` has not been established. `su root command` appears consistent with the binary’s generic `LOGIN COMMAND...` usage string, but was not tested and is not part of the plan.

HondaHack is not the privilege mechanism found here. Its inspected feature path uses Xposed integration for display output; no HondaHack command/root daemon was established. The available evidence points to the already-installed SuperSU facility.

## Integrity finding and decision

The preserved file mode is critically permissive for a setuid-root executable: both group and other have write permission. That mode must not be treated as safe merely because the command previously returned UID 0. The archive does not prove the exact live file mode or current live hash. The prepared collector therefore verifies `/system/xbin/su` hash, owner, setuid bit, and non-writable group/other mode through ordinary read-only shell commands before it will invoke `su`; the currently preserved `06777` mode fails that gate. No live check was run in Step 40E2.

Using the existing binary needs no `adb root`, install, chmod, service enablement, config edit, or target-side file write. Whether invoking this specific SuperSU binary can create/update daemon state or persistent audit/log data is **UNKNOWN** from available source/artifacts. Therefore “no persistent configuration change required” is established, but “invocation has no persistent side effects” is not.

**Existing root path:** historically proven, but current binary-integrity gate is open.
**Second vehicle session:** NOT READY.
**Next step:** resolve the archived/live `su` mode discrepancy and obtain independent review before any privileged collection.
