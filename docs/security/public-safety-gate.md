# Public-safety gate

`tools/check_public_safety.py` is the mechanical backstop that runs in Offline CI on every
pull request to `main` and on pushes to `main`. It reads Git objects (a range, the index with
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

Research Markdown is not blocked for living under `research/`; only the restricted directory
names above trigger PS007, and an entry with a reviewed reason clears one exact path.

## Allowlist

`docs/security/public-safety-allowlist.json` holds, per path pattern and rule, a ceiling and a
reason. The default is zero, so a new violation fails; more matches than the ceiling fail even
in a listed file; a listed file cannot hide a different rule. The initial entries record the
state of `main` at `b9fa1a0` (account paths in historical text, and the restricted-name
directories) after an audit, so those do not count as new risk. When a candidate edits the
allowlist, the gate prints `PUBLIC_SAFETY_NOTICE`: a reviewer must read that diff.

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
