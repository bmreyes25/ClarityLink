# Public repository practices considered for ClarityLink

Reviewed public repository material on 2026-10-15 from Tesla's [fleet-telemetry](https://github.com/teslamotors/fleet-telemetry) and [vehicle-command](https://github.com/teslamotors/vehicle-command) repositories. This is a summary of publicly visible organization only; it does not claim access to or knowledge of Tesla internal engineering standards.

## Useful patterns

- **Explain the project and its operating boundary first.** Fleet Telemetry and Vehicle Command lead with a concise purpose, scope, and system description before deeper setup details.
- **Organize code and docs by use.** Vehicle Command separates tools, packages, examples, and protocol documentation. Fleet Telemetry links users to focused subsystem/configuration guides.
- **Make setup and tests reproducible.** Their READMEs identify toolchain requirements and concrete build or test commands; examples have their own context.
- **Keep contribution and security guidance visible.** Both projects publish contribution and security entry points; Fleet Telemetry's contribution guide describes issues and pull requests.
- **Use reviewable GitHub workflows.** The repositories expose PR templates and automated workflows. ClarityLink already has offline CI, issue templates, a PR template, and repository-health checks.

## ClarityLink application

ClarityLink now puts a short, accurate status and offline quickstart in its README; separates curated current status from the preserved research archive; indexes the CL-R0–CL-R8 sequence; names evidence and safety limits; and checks documentation links, milestone order, evidence paths, private-path patterns, and repository hygiene offline. The project remains intentionally small: no telemetry service, release system, container pipeline, or other infrastructure was added merely to imitate larger projects.

## Sources

- [fleet-telemetry README](https://github.com/teslamotors/fleet-telemetry)
- [fleet-telemetry contribution guide](https://github.com/teslamotors/fleet-telemetry/blob/main/CONTRIBUTING.md)
- [fleet-telemetry security policy](https://github.com/teslamotors/fleet-telemetry/blob/main/SECURITY.md)
- [vehicle-command README](https://github.com/teslamotors/vehicle-command)
- [vehicle-command protocol documentation](https://github.com/teslamotors/vehicle-command/blob/main/pkg/protocol/protocol.md)
