# GitHub settings checklist

Read-only review of `bmreyes25/ClarityLink` on 2026-10-03. Repository settings were not changed by this documentation pass.

| Setting | Status | Finding / owner action |
|---|---|---|
| Public visibility | **VERIFIED** | Repository API reports public. |
| Default branch | **VERIFIED** | `main`. |
| Issues | **VERIFIED** | Enabled. |
| Description and topics | **VERIFIED** | Existing description is accurate; current focused topics are `android`, `automotive`, `carplay`, `digital-twin`, `reverse-engineering`, and `honda-clarity`. No changes recommended. |
| Dependabot alerts/security updates | **VERIFIED** | Dependabot alerts API query succeeded with zero returned alerts; Dependabot security updates are enabled. Weekly version-update configuration is tracked separately in `.github/dependabot.yml`. |
| Secret scanning | **VERIFIED — DISABLED** | API reports disabled. Owner should enable secret scanning. |
| Push protection | **VERIFIED — DISABLED** | API reports disabled. Enable after reviewing the project's deliberate synthetic/test fixtures and ignore policy. |
| Private vulnerability reporting | **VERIFIED — DISABLED** | API reports disabled. Enable it so `SECURITY.md` has a private repository route. |
| Code scanning default setup | **NOT CONFIGURED** | API reports `not-configured`. A CodeQL workflow is included in the repository; owner should confirm its first successful run and resulting alert visibility. |
| Branch protection/ruleset | **VERIFIED — NOT CONFIGURED** | API reports no branch protection for `main`. Consider requiring successful Offline CI and review before merge. |
| Action allowlist / SHA pinning | **VERIFIED — RECOMMENDED** | API reports all actions allowed and SHA pinning not required. Consider narrowing allowed actions and requiring full commit-SHA pins under the project's maintenance policy. |

Manual owner checklist: enable secret scanning, push protection, and private vulnerability reporting; decide whether to protect `main` with required Offline CI/review; review action allowlisting and SHA pinning. Do not treat this checklist as evidence that any setting was changed.

## GitHub documentation

- [Repository best practices](https://docs.github.com/en/enterprise-cloud%40latest/repositories/creating-and-managing-repositories/best-practices-for-repositories)
- [Security and analysis settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository)
- [Dependabot version updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-version-updates)
- [CodeQL compiled-language workflow guidance](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/manage-your-configuration/codeql-for-compiled-languages)
