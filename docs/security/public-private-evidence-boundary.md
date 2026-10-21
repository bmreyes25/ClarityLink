# Public and private evidence boundary

## Public GitHub may contain

- Sanitized architecture, research methods, source URLs/revisions/licenses, evidence classifications, and bounded claims.
- Test plans and non-sensitive receipts, exact public source commit IDs, aggregate measurements, and reproducibility instructions.
- A description of what classes of private evidence are retained and the verification state of its backup/recovery controls.

## Keep in authorized encrypted private storage

- Honda firmware, proprietary APKs, raw Honda decompilation and binary analysis, private function addresses/hook recipes, raw vehicle logs/captures, identifiers, authentication material, MFi certificates/keys, paid-license material, private research bundles, and sensitive machine configuration.
- Raw or derived Honda evidence remains private even if it was collected read-only. Ignore rules are not proof of encryption, backup, or retention safety.

## Publication checks

Before staging, inspect every path and diff. Exclude generated logs, APKs, captures, credentials, signing material, private source trees, and machine-specific configuration. Scan the staged diff for secrets and proprietary content. Link only to authorized public sources. Record a public-safe summary of private evidence classes without content, path, identity, or secret values.

## Preservation verification

CL-MASTER-01 does not claim a private archive backup/recovery PASS. A separate authorized procedure must verify encrypted storage, at least one independent backup, and a recoverability check without publishing its contents. Record only date, scope, verification outcome, and sanitized receipt identifier.
