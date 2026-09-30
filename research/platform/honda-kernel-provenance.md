# Honda kernel binary provenance — Step 40D

## Immutable inputs and copy-only extraction

The existing local forensic `boot.img` was read without modification. Its SHA-256 is `37d928201d8861e3037c3e9be8254617eeadfe09e018e37a46500d0711d875cc`. It is an Android boot image with a 2,048-byte **boot-image component alignment/page field**; that format field is not evidence of the kernel VM page size. A kernel copy was extracted externally to `/tmp/clarity-step40d/honda-kernel.bin`, SHA-256 `1dd3e403311d5cd18f12284b2d9263a0999707f1f16d3d83df1d8c324428949a`. Original image and derived binaries remain outside Git.

The kernel copy contains `3.1.10+`, `vcm30t30`, and `VCM30T30` strings. The associated read-only properties identify `Honda/Andromeda/vcm30t30a:4.2.2/1.F1A2.45/21:user/release-keys`, `MY16ADA`, Android 4.2.2/API 17, and ARMv7 (`armeabi-v7a`). Available module vermagic strings are `3.1.10+ SMP preempt mod_unload ARMv7 `, supporting the target release/config characteristics but not recovering the full kernel configuration.

## ADA01 correlation

See [ADA01 source assessment](honda-ada01-source.md). The exact target kernel release is 3.1.10+, while the official ADA01 source archive's kernel tree is 3.4.108 and has generic Tegra support but no VCM30T30 board source. The archived source is classified **RELATED PLATFORM SOURCE**, not a match. A generic `tegra_defconfig` is only a candidate configuration and must not be used to assert target settings.

## Evidence boundary

The kernel build string is abbreviated by embedded NUL bytes in ordinary string output; the available evidence supports release and board identity but not a trustworthy full compiler/build-host/timestamp reconstruction. No executable code, kernel patching, module loading, or device interaction was used. Exact kernel source correspondence remains unproven.
