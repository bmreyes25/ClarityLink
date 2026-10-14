# R7E6A API17 legacy ADB absence probe

**Result:** `R7E6A_API17_LEGACY_ABSENCE_PROVEN` on isolated Android 4.2.2 / API17 / x86. The run-owned emulator and private ADB server were cleaned up; 59 ownership checks passed and `cleanup_failures` was empty. No Honda or physical Android target was involved.

The old `test -e` query against a missing exact path returned host status 0 with empty stdout and stderr. That observation confirms an empty response cannot establish absence. An exact `ls -ld <path>` query returned one line naming the path and `No such file or directory`. A regular file, symlink, and directory each produced their own metadata line and therefore did not satisfy the absence grammar. The probe removed each exact fixture and confirmed exact-path ENOENT afterward.

Evidence is kept in the ignored local file `build/r7e6/runs/api17-absence-probe-895c6acbd784.json`; it is not committed. The tracked parser accepts only the exact single-line ENOENT grammar with host status 0 or 1, and rejects empty, mixed, extra, or unexpected output. This is API17 emulator evidence, not Honda behavior proof.
