# R7E7D Test A readiness decision

**Decision:** `R7E_TEST_A_EXECUTION_PACKAGE_READY`. Offline CI and aggregate CodeQL passed on exact HEAD `75c1fb332fd2a187a62a9ab29274484667c1c2d2`; all five CodeQL language jobs passed. The R7E7C directory parser fix was verified against preserved Honda output. Review of historical A0-WR output found and corrected two more compatibility mismatches: two-space MD5 formatting and the manifest-relative push source differing from the executed source. Inventory and ENOENT parsers were also tightened to evidence-backed formats. See [R7E7D compatibility review](r7e7d-test-a-legacy-compatibility-review.md).

**Next:** request a fresh, explicit Test A authorization bound to the final repository HEAD and identities below. Previous R7E7B and R7E7C authorizations are consumed. Test A remains `NOT_AUTHORIZED` and `NOT_EXECUTED`; Test B remains unauthorized.

Current package: collector SHA-256 `7cae443313ebe0d27d67bb08b32b140897c3b4d33f7e312d3323d70f37b8f129`; manifest version `R7E7D-TEST-A-COMMAND-SET-4`, SHA-256 `553f3dcf44e51bf91433838fccbcdfe6ec2b5af84608de61c6228daa96eb6b5e`; artifact SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`, MD5 `6137a693a77646aaf9a4cf0f351731d4`, size 7,904 bytes, staging mode `0555`; exact target `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`.

R7E7D issued zero Honda commands and caused zero Honda writes. The prior Test A attempt remained pre-push and pre-execution. Independent ECC review was unavailable; manual ECC-guided security, compatibility, process-lifecycle, and authorization review was recorded. Exact-head checks are documented in the R7E7D result after they complete.

---

# Historical R7E7C Test A readiness decision

**Decision:** `R7E_TEST_A_EXECUTION_PACKAGE_READY`. Exact-head Offline CI and aggregate CodeQL passed on `84a3819f2ed9cc1f7b614c1e9548671e4ce693d5`; all five CodeQL language jobs passed. The final documentation-only commit must also retain passing checks.

**Next:** after final exact-head checks, request a new hash-bound Test A authorization.

The R7E7C read-only observation established that `/data/local/tmp` still has the expected `drwxrwx--x` mode and `shell:shell` owner/group. Android emitted the legacy one-line `ls -ld` form with date/time and basename `tmp`; it omitted the size and full path required by the previous parser. The correction accepts this observed format while retaining strict mode, owner, group, and final-name checks. See [R7E7C review](r7e7c-test-a-directory-metadata-review.md).

Current package: collector SHA-256 `3ab879b59bb5f56a742381e5429e2b469f9ae2f1aa11535e74cac107394ebfdc`; manifest version `R7E7C-TEST-A-COMMAND-SET-3`, SHA-256 `299f4423f716a9fc5c4d11d921e2c38fe3f75134a30db517762ef3daec7a339a`; artifact remains unchanged at 7,904 bytes. The current [authorization packet](r7e6-test-a-authorization-packet.md) is not authorization to execute.

R7E7C used exactly two read-only Honda ADB commands. Honda writes: zero. Test A push attempts: zero. Diagnostic executions: zero. Test A retries: zero. R7E7C authorization is exhausted. Test A remains **NOT_AUTHORIZED** and **NOT_EXECUTED** under this new package. Test B remains unauthorized.

Independent ECC review was unavailable; manual ECC-guided review was recorded. Hosted checks for `84a3819f2ed9cc1f7b614c1e9548671e4ce693d5`: [Offline CI passed](https://github.com/bmreyes25/ClarityLink/actions/runs/38191726609); [aggregate CodeQL and all five language jobs passed](https://github.com/bmreyes25/ClarityLink/actions/runs/38191726604).

# R7E7F superseding decision — 2026-10-11

**Decision:** `R7E_TEST_A_RECOVERY_PACKAGE_READY`. This means only that the shell defect is reproduced/corrected offline and a separately authorized read-only recovery package is prepared. **Test A is not ready to retry.** The previous authorized attempt transferred the executable and invoked `--version` once, but process absence was not confirmed and cleanup/final absence were not attempted. Current Honda state is unknown.

Current corrected collector: `acee02afd1eaef3aab5b4d4b24ded8044fce67e6461c1d4883b552c87465deb5`; manifest `R7E7F-TEST-A-COMMAND-SET-5`, SHA-256 `20e93f4692e423851b1195d7c52db1c42e5088126faee2db8c993622611ab6c9`. Artifact unchanged. **Next:** separately authorize Phase R read-only inspection and stop for review; Phase C cleanup requires its own later authorization. No Test A retry/Test B is authorized. R7E7F Honda commands and writes: zero.
