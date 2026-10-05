# R6 ADR — custom receiver is the primary architecture

Status: accepted for offline engineering, 2026-10-04.

Decision: ClarityLink will develop a clean-room Honda-compatible CarPlay receiver that owns one session with primary Type110 and secondary Type111. R5Z's Python code is the host reference. The target implementation and Honda adapters remain evidence gated. Immediate target is real iPhone Type111 through a host receiver to a displayed decoded frame (R6-L7).

Rationale: [R3C](../../step-reports/43t1-r3c-static-entry-ownership-closure.md) parked stock `jmcs` runtime interposition; [R5D](../../step-reports/43t1-r5d-artifact-provenance-closure.md) found a promising descendant package name but no lawful receiver artifact; the [final R6A audit](../runtime/r6a-honda-receiver-substrate-audit.md) still lacks a complete additive Type111 ownership path. R5B–R5D remain supporting research. Honda USB/iAP2/MFi, audio, controls, displays and lifecycle are concrete adapter blockers.

Consequences: preserve Type110 direction and stock-quality audio/controls as mandatory for eventual target equivalence. No Honda execution, installation, startup change or live Type111 test is authorized here. R3C's stock interposition gate remains parked. Revisit only if all eight additive ownership edges are proven together.
