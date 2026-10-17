# Decision 0001: authoritative status with preserved history

- **Date:** 2026-10-15
- **Status:** Accepted for CL-R0 review

## Context

ClarityLink has large rolling status, roadmap, next-action, and evidence files alongside newer Test 6A/6B/7 findings. Moving the archive would risk breaking old links and losing provenance; keeping multiple documents labeled current would make the project ambiguous.

## Decision

Use `docs/status/current.md` and `docs/status/milestones.json` as the current status authority. Use `docs/roadmap/final-development-plan.md` as the active CL-R0–CL-R8 plan. Keep existing root ledgers and all historical reports at their established paths, mark their role clearly, and link to the authoritative pages. Validate milestone order, status state, safety flag, and evidence paths in the existing offline repository-health check.

## Consequences

Readers get a short current entry point while history and evidence retain their path and detail. Contributors must update the current summary and manifest together. This decision does not approve implementation, emulator, phone, or vehicle work.

## Evidence and review

The status baseline is the [Test 6A/6B/7 final readiness report](../../research/vehicle/test6a-t7-integration/18-final-readiness.md). The CL-R0 review packet lists exact local files and SHA-256 hashes. Independent ECC review remains pending for this decision and the CL-R0 documentation changes.
