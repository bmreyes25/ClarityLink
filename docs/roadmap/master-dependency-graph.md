# CL-MASTER-01 dependency graph

```mermaid
flowchart TD
  R4[CL-R4 / R7 API17 lab accepted]
  R10[CL-R10A/B/C merged evidence]
  R11[CL-R11-A evidence acquisition reconciliation]
  R13[CL-R13-A REA and xcertplay references]
  HH[CL-HH-06 HondaHack offline reconstruction]
  SYS[CL-SYS-01 factory Android architecture]
  R12[CL-R12-F API17 runtime and performance closure]
  REC[CL-REC-01 authorized independent Type111 bench]
  IF[CL-IF-01 receiver and display contract gate]
  OBS[CL-OBS-01 narrowly scoped read-only observation]
  INT[CL-INT-01 gated implementation]
  VT[CL-VT-01 vehicle acceptance]
  REL[CL-REL-01 alternative architecture decision]

  R4 --> R12
  R10 --> IF
  R11 --> IF
  R13 --> HH
  R13 --> SYS
  R13 --> REC
  HH --> SYS
  HH --> IF
  SYS --> IF
  R12 --> INT
  REC --> IF
  IF --> OBS
  IF --> INT
  OBS --> INT
  INT --> VT
  IF -. unsupported or unsafe contract .-> REL
  VT -. no-go or unmet acceptance .-> REL
```

Dashed edges mark a possible no-go path, not permission to conduct an experiment. `CL-OBS-01` only begins after a specific question, independent review, fixed read allowlist, and separate explicit owner approval. `CL-INT-01` and `CL-VT-01` remain disabled until their gates pass. Keep `safeForHonda() == false`.

## Gate order

1. Reconcile public and private evidence without importing unpublished commits into this roadmap.
2. Close offline reference and system reconstruction work.
3. Restore reproducible API17 runtime and establish measurable lab performance.
4. If separately approved, prove a genuine Type111 stream on an independent bench receiver; this does not prove Honda compatibility.
5. Establish both Honda receiver and cluster contracts from authorized sources. Either unresolved contract keeps Honda integration NO-GO.
6. Consider only the minimum read-only target observation needed to answer a named unresolved question and only after its separate review and approval.
7. Implement offline against approved interface contracts; then separately review and authorize any vehicle test.
8. If the target contract is unavailable, complete CL-REL-01 and report the original finish line as unachieved.
