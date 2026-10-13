# R7E7I current-process evidence contract

`tools/r7e7i_current_process_evidence.py` is an offline parser/classifier. It never enumerates `/proc` and is not a target collector.

An evidence producer would need two bounded inventories within one boot, full visibility, exact path and regular-file device/inode identity before and after, and for every visible PID: `/proc/PID/stat` state and starttime, `/proc/PID/exe`, complete `maps`, and covered `fd` entries. Receipts must hash-bind raw inputs. Any permission error, parse error, inventory race, PID generation change, unavailable field, identity change, or unexplained launch source yields an inconclusive/blocking result.

Matching is by device/inode, never basename, size, MD5 or textual path alone. A `(deleted)` mapping or descriptor can still refer to the exact inode. PID plus starttime distinguishes a generation from PID reuse. A zombie has exited and has no live address space, but remains unreaped; it is reported distinctly. Open descriptors and mappings are considered. Parent reaping does not itself establish that no other process or relaunch source exists.

Even a complete two-snapshot absence result is bounded in time. It cannot exclude a subsequent launcher, operator action, scheduled job, service restart or race. `future_launch_exclusion` remains `NOT_PROVEN_BY_SNAPSHOT`; cleanup and Test A authorization are always false. Synthetic inputs produce `MODEL_ONLY_*` decisions. Android 4.2.2/Linux 3.1 evidence must not depend on newer pidfd interfaces.

Procfs references: Linux [`/proc/PID/stat`](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html), [`exe`](https://man7.org/linux/man-pages/man5/proc_pid_exe.5.html), [`maps`](https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html), and [`fd`](https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html). The parser handles `comm` parentheses by anchoring from the final `) ` delimiter. It is not a substitute for a raw-evidence collector or reviewer.
