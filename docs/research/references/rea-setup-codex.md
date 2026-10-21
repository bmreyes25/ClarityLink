# REA setup for Codex

## Installed configuration

REA `rea-agents` **6.7.0** was installed from the official npm package and configured for Codex only. Node 24.18.0 and npm 11.16.0 meet the package's verified Node requirement (24.11+). The setup created a Codex MCP entry and installed the matching REA skill (version 42; 207 tool definitions). A configuration backup was made by the setup process.

Ghidra 12.1.4 was installed through Homebrew for ARM macOS, with OpenJDK 21.0.13. The provider is Apache-2.0 licensed; Java and Ghidra reside in normal package-manager locations and are not encoded as personal paths here. No licensed provider was installed.

## Reproduction and verification

Use the official [REA installation guide](https://github.com/morluto/rea/blob/7c6c25dda75e2d1d595a6cacc5cf9a82607f8502/docs/installation.md) and package. First preview the Codex-only changes with the pinned package's `setup --client codex --dry-run --json`; then run `setup --client codex --yes --format json`. Do not use `--all-detected` for this setup.

The scoped doctor was run for Codex, the skill, and Ghidra. It reported the Codex registration, skill alignment, and Ghidra 12.1.4 available. The complete environment was not declared healthy because other optional providers were not installed; live-server state was reported as unknown by the doctor.

A self-authored ARM64 Mach-O fixture was analyzed locally. REA CLI and MCP returned an overview, procedures, a string, xrefs, function analysis, and an evidence bundle of six records. Direct MCP initialization exposed 207 tools. This verifies the stdio server and Ghidra-backed smoke path; it does not verify that an already-running Codex desktop session reloaded the new MCP entry.

## Restart, updates, rollback

Restart or reload the Codex desktop session to make the new tools visible, then check the MCP tool list and run a small local fixture before using the provider. Update deliberately with a reviewed version and the same Codex-only setup; inspect its dry-run first. Before rollback, preserve the generated configuration backup, remove only the REA MCP/skill entries through supported client-scoped procedures, and confirm unrelated Codex entries remain. The general REA uninstall command is broader than client-scoped setup, so do not use it without first inspecting its effects.

No Honda binary, firmware, credentials, live iPhone, or vehicle was used. Local REA use does not by itself guarantee that agent-visible analysis output stays local; do not submit sensitive artifacts to an external model/provider without authorization.
