# Public-safety gate

`tools/check_public_safety.py` is the mechanical backstop. The authoritative run is
`.github/workflows/public-safety.yml`, which executes the scanner **from the protected base commit**;
the step in Offline CI runs the candidate's own copy and is supplementary evidence only. It reads Git objects (a range, the index with
`--staged`, or every tracked file with `--all`), so it checks what would actually be
published and never looks at ignored local files. It prints rule, path and line only, never
the matched value. It does not replace reading the diff.

| Rule | Fails on |
|---|---|
| PS001 | forbidden extension: firmware, APK/DEX/ODEX, native libraries, archives, packet captures, keys and certificates, media, databases |
| PS002 | opaque binary content: NUL bytes or an executable/archive/capture magic number in a non-image file |
| PS003 | a file over 1 MiB (images included) |
| PS004 | high-confidence credentials and private keys |
| PS005 | VIN-like identifiers (public sample VINs may be listed) |
| PS006 | absolute paths that name a local account (`/Users/<name>/`, `/home/<name>/`) |
| PS007 | a file under a restricted research directory name (`captures`, `acquisition`, `extracted`, `decompiled`, `deodexed`, `firmware`, `evidence`, ...) that is not explicitly allowlisted |
| PS008 | the candidate modifies or deletes the scanner or the protected workflow |
| PS009 | the candidate's allowlist grants more than the trusted one: a new entry, a broader path, a higher count, or a new sample exclusion |
| PS010 | a Git object the gate cannot safely inspect: a gitlink (submodule), a symlink pointing outside the repository, or an unsupported mode |

PS001-PS007 can be allowlisted; PS008-PS010 cannot. Anything the gate cannot read or parse (an
unresolvable trusted ref, a missing or invalid allowlist, a Git failure) exits with status 2 and is never a pass.

Research Markdown is not blocked for living under `research/`; only the restricted directory
names above trigger PS007, and an entry with a reviewed reason clears one exact path.

## Trust model

The exemptions that apply come from a **trusted ref** (in CI, the protected base commit), never from
the candidate being judged. The candidate's own allowlist is only compared with it: removing or lowering
an entry is fine, widening anything fails with PS009 until a separate update to the trusted baseline is
reviewed and merged. A candidate that changes the scanner or the protected workflow fails with PS008 by
design; such a change needs the owner's explicit approval rather than passing its own check. In the
protected workflow the candidate is fetched as Git objects and read with `git show` and `git diff`; it is
never checked out, installed, built or executed (a candidate with no allowlist file of its own, such as a branch cut before the trusted allowlist existed, simply gets no exemptions beyond the trusted ones; an unparseable allowlist is an error), the job has read-only permissions and no secrets, and
values from the event reach the shell only through environment variables.

Limits of that design, stated plainly:

- `pull_request_target` workflows run from the default branch, so the protected check applies only after
  it is merged. Until then the gate is **not** independently enforced; the result of the supplementary
  step in `ci.yml` is untrusted evidence, and a reviewer must read the scanner and the entire allowlist.
- The bootstrap is explicit: with a trusted ref that has no allowlist the gate refuses (exit 2) unless
  `--allow-bootstrap` is passed, and then prints `PUBLIC_SAFETY_BOOTSTRAP_UNTRUSTED`. Once the allowlist
  exists on `main` the flag has no effect, and a candidate cannot delete the baseline it is judged by.
- The check only blocks merging if it is made a required status check or a ruleset rule, which is a
  repository-owner decision that this change does not make.
- `--staged` (used by the local publisher) defaults to `origin/main` and tolerates the bootstrap case; it is
  a pre-commit convenience, not the gate.

## Allowlist

`docs/security/public-safety-allowlist.json` holds, per path pattern and rule, a ceiling and a
reason. The default is zero, so a new violation fails; more matches than the ceiling fail even
in a listed file; a listed file cannot hide a different rule. The initial entries record the
state of `main` at `b9fa1a0` (account paths in historical text, and the restricted-name
directories) after an audit, so those do not count as new risk. The allowlist file is itself scanned
like any other file, so a credential placed in an entry's reason is found.

## What the baseline audit found

All refs, 609 commits, 4,400 blobs: no binary, archive, image-container or key file type and no
blob over 213 KB; no private key; one VIN-like string, the public sample VIN used as a redaction
test fixture; 18 gitleaks `generic-api-key` hits, all SHA-256 build digests next to "API17"
labels (documented in `.gitleaks.toml`); 57 absolute paths naming the maintainer's local
account on `main`, 428 across history. Removing the account paths from history needs a history
rewrite, which requires explicit owner authorization and is not done here.

## Limits

A pattern gate misses what it does not describe. It does not know whether a text file is a
private capture, and it does not apply to Actions artifacts. Treat a pass as "none of these
checks failed", never as "safe to publish". Ignored files are not protected by being ignored: a
`.gitignore` is not storage, and irreplaceable private evidence needs a verified backup before
any relocation.
