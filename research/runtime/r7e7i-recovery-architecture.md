# R7E7I recovery architecture

1. **Preserve:** raw historical records remain byte-for-byte unchanged and hash-identified.
2. **Measure host:** optional time sampler uses monotonic duration plus independent read-only NTP queries; its unauthenticated status is explicit and it cannot emit an attestation.
3. **Analyze chronology:** source receipts are checked against Git and Actions metadata; output cannot infer numeric clock error absent a trusted bound.
4. **Model process evidence:** offline parser binds supplied procfs records to exact device/inode and fails closed on incomplete visibility, parse errors, PID reuse, or relaunch uncertainty.
5. **Rehearse only:** tests use synthetic procfs and fake ADB. Existing device-facing tools remain gated/default-disabled.
6. **Decide:** subsystem statuses remain independent; no combination of host time or fixture evidence grants target authorization.

Evidence files are private (directory 0700, file 0600). A digest detects later byte changes but does not prove who created the evidence. A detached signature requires an independently pinned reviewer fingerprint and does not prove the signer's clock accuracy. No generated reviewer key or synthetic attestation is permitted.
