# REA-assisted reverse-engineering method

This is an original ClarityLink workflow summary informed by 0xMovez's [11-step article](https://x.com/0xMovez/article/2109604520770548146) and the pinned [REA documentation](https://github.com/morluto/rea/tree/7c6c25dda75e2d1d595a6cacc5cf9a82607f8502/docs). The supplied PDF was not independently available for page-level review; the article is cited as a source, not reproduced.

1. **Choose the analysis engine.** Use REA to call a real parser/disassembler/decompiler; distinguish tool output from model inference.
2. **Install narrowly.** Verify package identity/version, requirements, permissions, planned files, backup, and client scope before applying setup.
3. **Classify the target.** Select source inspection for source, JADX for APK/DEX, and a native engine for ELF/Mach-O; start with the least complex suitable method.
4. **Reconnaissance.** Record format, architecture, imports/exports, relevant strings, and likely responsibility boundaries. Avoid indiscriminate dumps.
5. **Focused analysis.** Follow references and call paths from one explicit question; retain artifact identity and evidence links in authorized storage.
6. **Annotate carefully.** Describe inputs, outputs, state, callers, callees, and errors. Mark confidence and uncertainty; do not present guessed names as original intent.
7. **Bound hard cases.** Note obfuscation and analysis limits, set a stopping point, and do not extract credentials, bypass authentication, or defeat cryptography.
8. **Coordinate narrow investigations.** Give each worker one question and shared evidence labels; reconcile disagreements instead of accumulating duplicate claims.
9. **Write behavior specifications separately.** State observable inputs, outputs, state transitions, errors, and acceptance tests without copying proprietary code, symbols, or addresses. Clean-room practice is not legal advice or a guarantee of permission.
10. **Implement modularly.** Use explicit interfaces, ownership, and lifecycle; preserve accepted ClarityLink components absent evidence for a change.
11. **Verify behavior.** Cover normal, boundary, invalid, transition, teardown, recovery, and ownership cases. A synthetic match proves only the fixture behavior.

## Reusable evidence record

`Question | Artifact/version | Method/tool version | Observation | Inference | Confidence | Evidence reference | Privacy class | Limitations | Stop condition`

Use repository [evidence classifications](../../development/evidence-classification.md). At minimum distinguish source observation, project test, author-reported test, independent runtime observation, inference, and unknown. Do not promote one category into another.
