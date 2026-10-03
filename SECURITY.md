# Security policy

## Supported versions

ClarityLink is a research repository with no released supported product versions. Security fixes, when applicable, are developed on the current `main` branch.

## Reporting a vulnerability or vehicle-safety concern

Do **not** post credentials, exploitable details, private captures, firmware, or personal data in a public issue or pull request. Include only enough non-sensitive information publicly to request a private reporting route.

The repository's GitHub Private Vulnerability Reporting setting was checked on 2026-10-03 and was **disabled**. The repository owner should enable it. Once available, use GitHub's **Report a vulnerability** flow on the repository's Security / Advisories page to send details privately. Until that route is available, do not publish sensitive technical details; open a minimal public issue asking the maintainer to arrange private contact, without reproducer, exploit, identifiers, or secrets.

For a concern that could affect vehicle or occupant safety, stop testing and do not share vehicle identifiers or raw evidence publicly. Follow the same private-reporting boundary and identify the affected project area without posting operational exploit details.

## Data handling

Never include API keys, passwords, tokens, private keys, raw Honda/iPhone captures, proprietary firmware, or unredacted personal information in GitHub issues or pull requests. Use sanitized logs only. See the [vehicle-testing guide](docs/safety/vehicle-testing.md).
