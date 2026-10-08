# R7C6 memory observation

The current 100-cycle API17 Dalvik run logged baseline, warmup, each ten-cycle
sample, and the final cycle in the host-captured log. PSS KiB: baseline 6,428;
warmup 6,762; cycles 10–100: 6,431, 6,500, 6,434, 6,488, 6,159, 6,211,
6,172, 6,208, 6,224, 6,240. Native heap allocation remained approximately
10,554,296 bytes after warmup. The run does not show clear monotonic growth.
The project-owned resource counters and FD baseline returned to zero after
every cycle and remain the authoritative leak check.

The combined race run was stopped before the final cleanup/GC observation,
after its Activity-destroy phase failed to reach a durable `onDestroy()`
completion. Thus no final post-GC value is claimed for this run.
