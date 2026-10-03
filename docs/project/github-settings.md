# GitHub settings checklist

Repository settings reviewed and updated on 2026-10-03 for the listener security maintenance. GitHub CLI confirmed administrator permission before applying the explicitly requested minimum `main` protection.

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
| Code scanning default setup | **NOT CONFIGURED** | API reports `not-configured`; the tracked CodeQL workflow nevertheless completed successfully on 2026-10-03, and the wildcard listener alert is fixed by the code change. |
| Branch protection | **VERIFIED — CONFIGURED** | `main` blocks force pushes and deletion. Required status checks and PR reviews are not enabled; direct pushes remain allowed. Admin enforcement is enabled. |
| Action allowlist / SHA pinning | **VERIFIED — RECOMMENDED** | API reports all actions allowed and SHA pinning not required. Consider narrowing allowed actions and requiring full commit-SHA pins under the project's maintenance policy. |

## Manual branch protection steps

The low-friction protection is already applied. To review or change it manually, open **Settings → Rules → Rulesets or Branches**, target `main`, and verify **block force pushes** and **block deletion**. Optional stronger settings for a future workflow change: require a pull request before merging, require the exact status checks `Offline CI` and `CodeQL` (both verified from recent workflow runs), and require the branch to be up to date before merging. Requiring PRs would stop direct pushes.

Other owner actions still pending: enable secret scanning, push protection, and private vulnerability reporting; review action allowlisting and SHA pinning.

## GitHub documentation

- [Repository best practices](https://docs.github.com/en/enterprise-cloud%40latest/repositories/creating-and-managing-repositories/best-practices-for-repositories)
- [Security and analysis settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository)
- [Dependabot version updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-version-updates)
- [CodeQL compiled-language workflow guidance](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/manage-your-configuration/codeql-for-compiled-languages)
