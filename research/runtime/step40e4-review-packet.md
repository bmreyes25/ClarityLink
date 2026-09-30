# Step 40E4 external review packet

**Independent review: NOT PERFORMED.** This is a compact handoff for a future independent reviewer, not an approval.

## Question and proposed operation

Question: can ClarityLink obtain current `jmcs` maps/smaps using a statically justified zero-persistent-write privilege path?

Proposed command under consideration only (placeholder PID; not run and not authorized):

```sh
/system/xbin/su -c "cat /proc/<pid>/maps"
```

The fixed Step 40F collector also proposed reads of `/proc/<pid>/smaps`, thread metadata, and `/proc/<pid>/fd`. Its host-side capture writes a restricted private bundle outside Git. That is a host write, so “zero-write” here describes target-side privilege acquisition only.

## Evidence and static-analysis limits

- Archived `su` SHA-256: `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`; ELF32 LE ARM EABI5, ET_DYN, Android linker, entry `0x3528`, version marker `2.77:SUPERSU`.
- The hash and mode `06777` match three preserved full-system snapshots of the already modified unit. No pristine factory image proves origin or mode provenance.
- CLI strings document `-c/--command`; imports/strings show filesystem, daemon, socket, policy/log, credential, process, and signal capabilities. The stripped mixed ARM/Thumb binary did not yield trustworthy callsite arguments, open flags, or a complete `-c` control-flow trace. No exact callsite address for write operations is claimed.
- Critical address available: ELF entry `0x3528`; reliable branch/call addresses: **not recovered**. Temporary pyelftools/Capstone analysis was host-side only. The archived ARM binary was neither executed nor emulated.
- The prior Step 40E capture shows shell UID 2000 can read process/thread metadata and global `/proc/net`, but receives permission denied for the target process `maps`, `smaps`, and `fd` in all three phases.
- Archived ADB defaults are `ro.secure=1`, `ro.debuggable=0`, user/release-keys; observed shell UID was 2000. No supported no-`su` root transition is established.
- `dumpstate` via `bugreport` is a plausible shell-to-root diagnostic path with all-process smaps strings, but is broad and has unexcluded signals and persistent output behavior. It is not approved or considered zero-write.
- No SUID/SGID helper or existing root service was proven to provide narrow arbitrary target-proc reads safely.

## Risk conclusion

`su -c` zero-persistent-write: **NOT PROVEN**. SuperSU request/log/policy/daemon behavior and open flags are unresolved. HondaHack’s separate runner deletes SuperSU logs and performs persistent system changes; it is not a safe wrapper or mitigation. Exact active SuperSU configuration/daemon/policy state is not established by archived data.

Definition used: zero-persistent-write excludes intentional filesystem/block-device create, modify, truncate, rename, unlink, chmod, chown, relabel, update, or persistence. RAM-only process state, anonymous mappings, pipes, sockets, Binder/kernel bookkeeping, tmpfs, and read-induced atime are distinguished and documented separately. Atime is not used to excuse application writes.

## Decision and assumptions

Outcome: **NO JUSTIFIABLE PRIVILEGED PATH** on current evidence. Keep Step 40F and Step 41 blocked; Type111 remains disabled. Step 40F-Lite is already represented by the saved Step 40E ordinary-shell three-phase capture and should not trigger a duplicate vehicle session.

Assumptions/limits: snapshots represent a modified unit; they do not prove current live configuration. String/import evidence proves capability, not reachability. `dumpstate` static strings do not prove exact service-path behavior. No independent review has occurred.

## Reviewer focus

An independent reviewer should challenge (1) whether any archive contains exact matching SuperSU source/build/config capable of closing the `-c` write path, (2) whether `dumpstate -s` can be proven not to signal processes or persist output, and (3) whether Step 41 truly requires fresh mappings/page-size evidence or can be redesigned around already captured unprivileged data. Do not run the proposed command or any candidate service during review.
