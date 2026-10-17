# Local ECC review configuration

ClarityLink's ECC reviewer roles are project-local and intentionally excluded
from Git. The active configuration enables Codex multi-agent review with a
maximum of four threads and one delegation level. It defines `reviewer` and
`security_reviewer` roles in `.codex/config.toml`; each role uses
`sandbox_mode = "read-only"` and instructions that prohibit file changes,
staging, commits, vehicle operations, and live iPhone operations.

To restore these roles in a local checkout:

1. Create `.codex/agents/` at the repository root.
2. Create `.codex/config.toml` with `[features] multi_agent = true`,
   `[agents] max_threads = 4` and `max_depth = 1`, and role tables pointing to
   `agents/reviewer.toml` and `agents/security-reviewer.toml`.
3. Set both role files to `sandbox_mode = "read-only"`, a review-appropriate
   model and reasoning level, and instructions to review an exact Git range,
   report evidence-backed findings with severity and file/line references, and
   never modify files or perform vehicle/iPhone operations.
4. Start a new Codex task in the checkout and verify that both named roles are
   available before relying on them.

Do not copy machine-specific paths, credentials, or global Codex settings into
the project. ECC review is an independent AI assessment; it is not human
vehicle-safety approval.
