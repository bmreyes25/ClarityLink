# R7E7I clock source comparison

| Source/method | What it can support | Limitation for historical attestation |
|---|---|---|
| Local wall clock | Timestamp labels and within-process samples | May be stepped or mis-set; no independent calibration evidence |
| Monotonic clock | Elapsed duration and wall/monotonic divergence during one boot | Has no UTC epoch; cannot independently date an old event |
| Ordinary NTP replies | Offset/delay/root metrics; independent source comparison | Replies here are unauthenticated and path/source can be wrong or spoofed |
| NTS authenticated NTP | Authenticated association to configured NTS server | Authentication does not itself guarantee UTC accuracy or historical state |
| Signed timestamp authority token | Digest existed no later than token generation time | A token obtained now cannot retroactively time the old event |
| Signed reviewer attestation | Reviewer key signed a hash-bound statement | Key ownership/provenance must be independently verified; signature is not clock calibration |

The collector `tools/r7e7i_host_time_evidence.py` records raw responses and bounded measurements. It detects and reports disagreement; it does not assert a trusted bound or produce an attestation. The observed three-source sample was consistent with sub-second estimated intervals, but the intervals inherit unauthenticated source and host-receive-time assumptions. It is evidence for investigation only.

For NTP offset and synchronization distance terminology see [RFC 5905](https://www.rfc-editor.org/rfc/rfc5905.html). NTS association authentication is specified by [RFC 8915](https://www.rfc-editor.org/rfc/rfc8915.html). A timestamp token's generation time and message imprint are defined by [RFC 3161](https://www.rfc-editor.org/rfc/rfc3161.html). A host monotonic clock is suitable for durations, not UTC conversion ([Python time documentation](https://docs.python.org/3/library/time.html)).
