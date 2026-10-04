# R5B — receiver component identification

## Scope/result

No lawful, versioned descendant payload was obtained. Therefore there are no R5B candidate components for file-level identification. This report intentionally contains no invented filenames, hashes, ELF properties, imports, exports, symbols, strings, or offsets.

| Candidate component | Filename | SHA256 | Architecture / bitness | Linkage | Imports/exports/symbols/strings | Role | Confidence |
|---|---|---|---|---|---|---|---|
| Descendant `jmcs` | Not available | N/A | N/A | N/A | Not inspected | Public `ic1101` notes report `jmcs` decompilation for its family; this is source-note evidence, not an R5B binary observation | Family-level lead only |
| AirPlay/CarPlay receiver libraries | Not available | N/A | N/A | N/A | Not inspected | Unknown | Unknown |
| Screen/display services | Not available | N/A | N/A | N/A | Not inspected | Unknown | Unknown |
| APK/JAR/ODEX components | Not available | N/A | N/A | N/A | Not inspected | Unknown | Unknown |

The R5A checklist terms (`AirPlayReceiverSessionScreen`, `ScreenRegister`, `AirPlay_DeriveAESKeySHA512ForScreen`, `streamConnectionID`, `dataPort`, `SETUP`, `TEARDOWN`) remain a future search checklist only. No matching symbol or string was observed in a descendant artifact in this milestone. Symbol absence cannot be inferred from lack of access to the artifact. @ECC conclusion: `TYPE111_INSUFFICIENT_ARTIFACT`.
