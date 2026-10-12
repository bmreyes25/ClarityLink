# R7E7D Test A collector verification

See the [R7E7D legacy compatibility review](r7e7d-test-a-legacy-compatibility-review.md) for the complete parser contracts and historical Honda evidence. Collector SHA-256 is `7cae443313ebe0d27d67bb08b32b140897c3b4d33f7e312d3323d70f37b8f129`; manifest version `R7E7D-TEST-A-COMMAND-SET-4`, SHA-256 `553f3dcf44e51bf91433838fccbcdfe6ec2b5af84608de61c6228daa96eb6b5e`. Focused collector tests: 75 passed. Exact-head full suite/hosted results are recorded in the final R7E7D readiness entry. No Honda operation occurred in R7E7D.

---

# Historical R7E7C Test A collector verification

The current collector is bound to manifest `R7E7C-TEST-A-COMMAND-SET-3`. Collector SHA-256: `3ab879b59bb5f56a742381e5429e2b469f9ae2f1aa11535e74cac107394ebfdc`. Manifest SHA-256: `299f4423f716a9fc5c4d11d921e2c38fe3f75134a30db517762ef3daec7a339a`.

R7E7C corrected the parent-directory metadata parser after a separately authorized read-only Honda observation showed Android 4.2.2 output in legacy form: mode, owner, group, date/time, basename `tmp`; no size or absolute path. The check still requires one line, exact mode `drwxrwx--x`, exact `shell:shell` ownership, and exact last token `tmp` or `/data/local/tmp`.

Focused fake-ADB fixtures: 58 passed, including current legacy CRLF output, the prior size/full-path form, mode/owner/group/name mismatch, empty output, and extra lines. The full offline suite passed: 1,040 passed, 15 skipped; self-locator, simulator, repository-health, and whitespace checks passed. Exact-head Offline CI and aggregate CodeQL, including all five languages, passed on the parser correction commit; this documentation follow-up will be checked on its own final head. The default path remains `NOT_AUTHORIZED`; dry run must still report zero ADB operations.

Artifact SHA-256 remains `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`; MD5 remains `6137a693a77646aaf9a4cf0f351731d4`; size 7,904 bytes; staging mode `0555`. No artifact rebuild was made.
