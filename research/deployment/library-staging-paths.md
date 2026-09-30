# Candidate library paths for a future jmcs preload

No path is approved for deployment. All conclusions below are offline and based on preserved metadata.

| Candidate | Evidence | Remaining blocker | Current disposition |
|---|---|---|---|
| `/data/local/tmp/claritylink_jmcs_interposer.so` | UDA `/local/tmp` exists as mode 0771 shell:shell; a historical `/proc/mounts` capture lists `/data` as `rw,nosuid,nodev` without `noexec`; jmcs runs root | Honda policy/domain and linker executable-map permission unknown; bad preload may be fatal if Honda matches AOSP behavior | Best candidate for future evaluation; not proven mappable |
| `/data/local/claritylink/...` | `/data/local` exists | Child absent; policy/map permissions unknown | Not preferred absent evidence |
| `/data/claritylink/...` | UDA data filesystem | Child absent; policy/map permissions unknown | Not preferred absent evidence |
| `/system/lib/...` | APP system library directory exists | Requires persistent system partition change | Avoid for initial no-op design |
| `/vendor/lib/...` | No matching vendor lib path established in APP | Path and policy unproven; partition mutation likely | Not established |

The boot service currently sets no `LD_PRELOAD`; any init-scoped preload requires a boot-ramdisk change regardless of staging path. The historical noexec-negative mount observation reduces one risk but does not establish `mmap(PROT_EXEC)` permission: SELinux/process-domain and actual linker behavior are unknown. No filesystem path has proven read, map, and execution suitability for jmcs. Do not stage files or provide deployment steps until an explicitly authorized later milestone.
