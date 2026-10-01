# Contributing to ClarityLink

ClarityLink is an evidence-led car-integration and digital-twin project. Keep changes scoped, preserve the research record, and make the distinction between Honda facts and model assumptions visible.

## Evidence and data

- Use the labels in [evidence classification](docs/development/evidence-classification.md).
- Do not convert external prior art or synthetic tests into Honda facts.
- Include exact source paths, URLs, revisions, and claim scope where practical.
- Use synthetic fixtures in tracked tests. Keep raw Honda firmware, captures, keys, private logs, and personal data ignored/local.
- Do not rewrite historical evidence or delete milestone reports to make current status look cleaner.

## Project records

- Update `PROJECT_STATE.md` when a milestone materially changes known behavior or readiness.
- Update `EVIDENCE_INDEX.md` when evidence or its classification changes.
- Keep `NEXT_ACTION.md` to exactly one concrete technical task.
- Add a step report for a substantial milestone and link it from `step-reports/README.md`.

## Testing and live boundaries

- Run the relevant tests, preferably the canonical `./tools/run_tests.sh`.
- Run `git diff --check` before committing.
- CI is offline-only and must not require a vehicle, ADB, Honda firmware, private captures, keys, or proprietary APKs.
- Declare vehicle interaction level in pull requests. Live mutation requires its own reviewed milestone and rollback/stop conditions.
- Preserve Type110. Do not enable Type111 based solely on MHI2 or Apple evidence.

## Commits

Keep commits focused and use the project prefix with a concise imperative description:

```text
ClarityLink: add valid ScreenStream H264 fixture
ClarityLink: document Type111 prior art
ClarityLink: add ExternalDisplay renderer contract
```
