# Honda kernel runtime observations — Step 40E

## Manual preflight supplied by the user

Separate from the immutable automated capture, the user reports successful read-only shell reads showing:

- Linux `3.1.10+`, `SMP PREEMPT`, built Thu Apr 5 02:19:35 JST 2018
- gcc 4.6.x-google 20120106 prerelease
- ARMv7, four logical CPUs; implementer `0x41`, CPU part `0xc09`, revision 9
- Hardware `vcm30t30`, device `vcm30t30a`, board `Andromeda`
- Android 4.2.2 / API 17; ADB shell UID 2000 (`shell`)

The corrected collector independently matched `/proc/version` and Android release, SDK, device, board, and hardware properties. The manual output is not represented as part of the automated bundle.

## Automated read-only observations

The completed three-phase capture found the same `jmcs` process identity throughout. `/proc/<jmcs>/maps` and `smaps` were permission denied to the unprivileged shell, leaving page size and runtime mappings unknown. CPU0–CPU3 topology values were available during baseline; cache index directories were not exposed. `/proc/config.gz` had a gzip signature but the legacy ADB shell copy did not decompress, and `/sys/fs/selinux/enforce` was absent. No runtime permission, cache, signal, rendezvous, or patch test was performed.

Related Tegra source shows ptrace permission gates for `maps`/`smaps` and `/proc/<pid>/fd`; combined with shell UID 2000 and root-owned `jmcs`, this is the high-confidence explanation for the observed errors. Honda's exact 3.1.10+ source is not available, so this is not vendor-kernel confirmation. See [proc access analysis](honda-proc-access.md).

Static Step 40D evidence remains: copied Honda kernel SHA-256 `1dd3e403311d5cd18f12284b2d9263a0999707f1f16d3d83df1d8c324428949a`; exact kernel config remains unrecovered. The official ADA01 3.4.108 tree remains related-platform comparison source only.

Step 40E2 verified all 1,944 capture hashes offline. `/proc/meminfo`, captured maps errors, process status, proc mount options, ASLR, CPU topology, and the gzip failure were examined for indirect page-size evidence; page size remains **UNKNOWN**. No address alignment was used to infer a granule.
