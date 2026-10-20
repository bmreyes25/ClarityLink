# R7C6 native socket runtime evidence

The production `AndroidSocketAdapter` is exercised through JNI on API17
Dalvik, using AF_INET loopback and fragmented Type110/Type111 LAB envelopes.
The 100-cycle run captured in the R7C6 run log processed both streams via
socket → parser → receiver generation → H.264 decoder → Android Surface.
Per-cycle native owner counters and socket descriptor counts returned to
baseline. A focused active-read shutdown case also passed: the checkpoint was
reached, local shutdown returned, and reader/peer threads joined. The active
write shutdown case passed in the full logged race set.

This is not the full requested production socket fault matrix. API17 Dalvik
coverage still lacks explicit cases for connection refusal, port collision,
zero/oversized/malformed/truncated envelopes, wrong generation/stream, and
controlled partial writes. Type111 peer close and Type110/Type111 primary
failure policy do not yet cover the requested independent timeout, malformed,
truncated, oversize, and wrong-generation Type111 cases. These cells remain
blocked; Java `Socket` checks and host adapter tests are not substituted for
Dalvik production-adapter evidence.
