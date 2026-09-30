# Step 40C — Thumb veneer range and allocation model

The exact BL callsites are INFO `0x28a158` and Setup `0x28af72` (Step 40B evidence). For a Thumb BL at address `A`, the PC base is `A+4` and the signed encoded displacement is even, from `-2^24` through `2^24-2`. The derived inclusive even-address ranges are:

| Callsite | Reach |
|---|---|
| INFO `0x28a158` | `0x0`–`0x128a15a` |
| Setup `0x28af72` | `0x0`–`0x128af74` |
| Common veneer window | `0x0`–`0x128a15a` |

Intervals are clipped to valid ARM32 code addresses; the arithmetic lower endpoint before clipping is below zero for both sites. The common interval is a large theoretical address interval, not a statement that a free mapping exists. Android API 17 provides the Bionic `mmap2` interface, but a caller-provided hint is not proof of placement, and no collision-safe near allocator has been verified for the Honda kernel. A candidate allocation would have to be page-aligned, contain the entire veneer, land inside the common branch interval, be revalidated against actual mappings and returned address, and remain alive until both callsites are restored and no in-flight caller can use it.

The project implements a first-fit gap chooser over supplied synthetic intervals. It does not call `mmap`, reserve address space, or claim a real allocation strategy. A gap-snapshot allocator would race with concurrent mappings unless reservation is atomic and the actual returned address is checked. No `MAP_FIXED_NOREPLACE` support is assumed for this API/kernel generation.

`NEAR VENEER ALLOCATION: MODEL ONLY; TARGET NOT READY`

## Step 40E status

The three-phase Step 40E capture completed, but unprivileged ADB reads of `/proc/<jmcs>/maps` and `smaps` returned `Permission denied`. INFO/Setup runtime reach intervals, load bias, page size, and candidate free VA gaps therefore remain unknown. The analyzer preserves these as unavailable and does not infer empty address space. No allocation or active target operation occurred.
