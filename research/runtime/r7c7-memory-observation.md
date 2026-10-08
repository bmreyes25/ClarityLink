# R7C7 memory observation

PSS and native heap observations were captured from the final current-code API17 Dalvik run. Selected PSS values (KiB): baseline 6450; post-warmup/cycle 1 6534; cycle 10 6651; 20 6584; 30 6629; 40 6632; 50 6592; 60 6654; 70 6654; 80 6679; 90 6675; 100 6675. Native heap allocated bytes remained approximately 10,599,336 after warmup and 10,599,384 from cycle 20 through cycle 100. Post-GC sample was 10,608,488 bytes and PSS 7268 KiB; system state and collection timing differ, so this sample is not treated as directly comparable to cycle points.

Warmed cycle samples fluctuate within a narrow band and show no clear monotonic growth across the 100 cycles. This is bounded emulator evidence, not a production-device memory guarantee. Raw sampled log: `/tmp/claritylink-r7c7-combined-final-runtime-log.txt`.
