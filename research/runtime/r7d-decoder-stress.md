# R7D decoder stress

The R7D decoder mode repeats valid Type110 IDR decode/post across 25 receiver generations and verifies Type110 survives malformed Type111 media failures. The Type111 stream is recreated after isolated failure; the decoder/receiver generation is fully disposed each iteration.

**Result:** `R7D_DECODER_STRESS=PASS` on the owned API17 Dalvik emulator. Twenty-five Type110 IDR decode/post cycles passed. Five malformed Type111 NALs and one truncated Type111 NAL failed within Type111 scope; Type110 decoded afterward in all six failure cases. Type111 was then set up again and decoded valid H.264 in all six cases. Native owners returned to zero each generation.

Evidence: [`/tmp/claritylink-r7d-decoder-final.log`](/tmp/claritylink-r7d-decoder-final.log) and [`/tmp/claritylink-r7d-decoder-final-runtime.log`](/tmp/claritylink-r7d-decoder-final-runtime.log). Malformed NAL injection uses an explicitly lab-only synthetic packet seam. Transport truncation is separately covered by the R7C production socket matrix. No real codec/security behavior is claimed.
