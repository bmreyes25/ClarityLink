# Step 1 — Git and Evidence Baseline Changelog

**UTC time:** 2026-09-26 ~02:00  
**Starting Git HEAD:** `663ed02ae381dac3beba8a522f360606d9a6182f` (local)  
**Branch:** `main`  
**Remote:** `origin` → `https://github.com/bmreyes25/clarity-carplay-cluster.git`

## Files changed and purpose

| Action | File / path | Purpose |
|--------|------------|---------|
| Created | `research/evidence/second-display-ledger.md` | Evidence ledger: 12 claims tied to artifacts with confidence levels and missing proof columns |
| Created | `research/progress/` (directory) | Per-step progress tracking (did not exist) |
| Created | `research/progress/STEP_01_CHANGELOG.md` | This file |

## Source references / hashes (key artifacts)

| Artifact | SHA-256 | Status |
|----------|---------|--------|
| `research/native/receiver-multidisplay-audit.md` | `584c7192...aa914d5e` (10,125 B) | Observed, static ELF audit |
| `research/NATIVE_CARPLAY_CLUSTER.md` | `82e8a17a...52af8fd` (19,492 B) | Observed, static receiver audit |
| `research/REPORT.md` | `8cc5377b...c904` (36,554 B) | Live session + static findings |
| `research/acquisition/ACQUISITION_COMPLETION_20260926.md` | `3566ce0d...686bb7d` (4,236 B) | F-B verified complete |
| `research/acquisition/FORENSIC_STATUS_20260925.md` | `19eb4154...2a9dafbf31` (5,033 B) | Partial acquisition status |
| `research/acquisition/LIVE_INVENTORY_REVIEW.md` | `e2efae1e...9a47f804` (3,121 B) | Live inventory (114.3 GiB free) |
| `research/acquisition/STORAGE_MAP.md` | `9c383211...121248` (5,423 B) | Partition map |
| `research/captures/20260925T150706Z-SESSION_FINDINGS.md` | `6caf99a1...3283ecdddfe` (5,396 B) | Session observations |
| `research/captures/20260925-WAZE_HEADUNIT_FINDINGS.md` | `66c5862e...b563b758` (5,586 B) | Waze positive control |
| `research/contracts/cluster-stream-v1.schema.json` | `7d519f77...31eabdf4c5` (7,284 B) | Contract schema |
| `research/simulator/display-profile.json` | `4b457b89...9351b9a0` (701 B) | Display config fixture |
| `research/inventory/backup-checksums.json` | `a1ee24a9...43413c605` (4,478 B) | Original backup checksums |

## Commands executed and results

### Git status
- `git status --short` → **clean** (no uncommitted or staged changes before this step)
- `git log --oneline -5` → last commit `663ed02 docs: add bounded step 1-5 prompts and model assignments`
- `git remote -v` → origin `https://github.com/bmreyes25/clarity-carplay-cluster.git` (fetch and push)

### Tracked file inventory
- `git ls-files` → **117 tracked files**

### Security audit (no sensitive data tracked)
- `git ls-files \| grep -iE '\.(img|bin|tar|zip|keystore|pem|key|jks|p12|apk|dex|odex|so)$'` → **none**
- `git ls-files \| grep -iE 'credential|secret|token|password|private'` → **none**

### Ignore rules verification
- `git check-ignore --verbose research/captures/` → matched `.gitignore:8:/research/captures/` — **excluded**
- `git check-ignore --verbose research/native/` → **not ignored** (`.md` files intentionally tracked per `!/research/native/*.md`)
- `git check-ignore --verbose research/protocol/` → **not ignored** (dir does not exist yet)
- `git check-ignore --verbose research/progress/` → **not ignored** (dir does not exist yet)
- `git check-ignore --verbose research/evidence/` → **not ignored** (dir does not exist yet)

### Simulator tests
| Test suite | Tests | Result |
|------------|-------|--------|
| `python3 -m unittest discover -s research/simulator -p 'test_*.py'` | 4 | OK |
| `python3 -m unittest discover -s research/acquisition -p 'test_*.py'` | 8 + 12 + 3 = 23 | OK |
| `python3 -m unittest discover -s research/probes/carplay-coexistence -p 'test_*.py'` | 7 | OK |
| `python3 -m unittest discover -s research/probes/decoder-capacity -p 'test_*.py'` | 3 | OK |
| `python3 -m unittest discover -s research/scripts -p 'test_*.py'` | 7 + 2 + 3 = 12 | OK |
| `node test-contract-adapter.js` | — | Passed |
| `node test-dual-screen.js` | — | Passed |
| `node test-capture-replay.js` | — | Passed |
| `node test-guidance-expiry.js` | — | Passed |
| `node test-live-casting-replay.js` | — | Passed |
| `node test-waze-headunit-replay.js` | — | Passed |
| **Total Python tests** | **49** | **All passed** |
| **Total Node.js tests** | **6 suites** | **All passed** |

### Python syntax check
- `python3 -m py_compile` on all Python source files → **all compiled cleanly**

### Test artifacts not tracked
- `research/simulator/guidance-card` → ignored by `.gitignore`
- `research/simulator/guidance-ocr` → ignored by `.gitignore`
- Raw firmware/images → excluded
- `CLARITY_BACKUP_20260918_0225_ORIGINAL` → **not modified** (perms `0444`, 1,248 B)
- `CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL` → **not modified** (perms `0444`, 640 B)
- `CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING` → **not modified** (perms `0644`, 736 B)

## Findings

1. **Git baseline is clean** — no uncommitted changes, no staged files, no credentials or binary artifacts in the index.
2. **Evidence ledger created** — `research/evidence/second-display-ledger.md` has 12 claims covering receiver audit, decoder capacity, Honda Hack casting, Waze positive control, forensic acquisition, simulator tests, and display geometry. Each has a raw artifact reference, confidence rating, and explicit missing proof.
3. **All 49 Python and 6 Node.js test suites pass** — the existing simulator, acquisition, probe, and script tests are green.
4. **`.gitignore` correctly excludes** raw captures, firmware, build artifacts, credentials, and large data directories.
5. **Key single-screen call sites recorded** with binary evidence: `gMainScreen` at VA `0xb02aa` in `jmcs`, singleton callback in `libcarplay_proxy.so` at `0x1b7d`/`0x1be0`–`0x1c04`.
6. **Honda Hack settings** confirmed from session findings: center-screen mirror following Maps→Music, Honda compass visible on cluster during routing.
7. **Photo-derived navigation bounds** noted as approximate (Honda compass below speed gauge, above Menu/trip) with side clearance unverified.
8. **Forensic acquisition F-B** verified complete: 2,487 hashes passed in both Mac copies, 9-partition GPT validated, optional `/proc` reads denied in 158 attempts (recorded as unavailable).
9. **Historical claims that cannot be verified:** exact iAP2 Identification bytes, R15 protocol support, active-CarPlay decoder coexistence, and precise display-1 geometry — all marked **unknown** in the ledger.

## Confidence summary

- **High confidence:** receiver single-screen audit, singleton callback, decoder frame counts (CarPlay disconnected), Honda Hack center-mirror behavior, forensic acquisition verification, all simulator tests
- **Medium confidence:** pre-R15 screen integration (string absence), 28/30 frame gate margin, photo-to-display geometry
- **Low confidence:** exact navigation rectangle coordinates, protocol-level stream identity for cast, R15 string-key lookup logic
- **Unknown:** iAP2 Identification bytes, active-CarPlay coexistence, iPhone-rendered cluster stream support, R15 capability

## Limitations

- Static ELF analysis only; no runtime probe of receiver on live Honda hardware.
- `CONFIG_USB_MON` is unset, so raw iAP2 payloads were not captured.
- Photo-derived bounds are approximate; no calibrated display-1 measurement.
- Simulator tests exercise contract logic, not actual Honda receiver behavior.
- F-B optional reads were permission-denied in 158 attempts.

## Rollback

If needed:
- `cd /Users/bmreyes24/ClarityLab/clarity-analysis && rm -rf research/evidence research/progress`
- Remove only the new tracked files; original artifacts remain unchanged (both originals are read-only `0444`).
- Original backup at `/Users/bmreyes24/ClarityLab/backups/CLARITY_BACKUP_20260918_0225_ORIGINAL` was never touched.
- Original forensic copy at `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL` was never touched.

## Outstanding gates

- **Step 2 (Infotainment twin):** in progress — needs strengthened service/display fixtures
- **Step 3 (Decoder probe):** in progress — needs background-safe bounded variant
- **Step 5 (Static Identification):** in progress — raw Identification bytes unavailable
- **Step 6 (Protocol capture):** conditional pending — only if Step 5 leaves material uncertainty
- **Step 8 (Boot-independent recovery):** pending — requires separate review
- **Dependent gates 9–12:** all pending or blocked per current STEP_STATUS.md

## Next action

Push this step's changes to `origin/main` and verify the remote commit. Evidence ledger and progress directory are ready for Codex independent verification.
