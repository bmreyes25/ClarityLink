# Offline development and testing

## Requirements

- Python 3.12 or newer supported by the repository dependencies.
- Node.js for simulator JavaScript checks.
- FFmpeg with an H.264 decoder, RGBA output, and preferably `libx264` for the real synthetic encode/decode test. The Python test explicitly skips that case if a capability is missing; GitHub Actions installs FFmpeg and exercises it.
- No Honda firmware, vehicle, ADB, keys, or private captures are required by CI.

## Local setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-test.txt
```

On macOS, install FFmpeg separately with Homebrew if needed (`brew install ffmpeg`). On Ubuntu, install the distribution FFmpeg package. Capability checks are used instead of assuming a specific FFmpeg version.

## Canonical test command

```sh
./tools/run_tests.sh
```

The script runs Python tests, the host H.264/ScreenStream synthetic path, contract-only JavaScript simulator checks, hook-locator smoke checks, interposer tests, and `git diff --check`. It deliberately excludes replay scripts backed by observation/capture datasets (including scripts that expect ignored screenshot assets); those data are not CI inputs. Tests that require a local ignored forensic binary skip with a reason if that artifact is not present. CI must never download or require Honda artifacts or private captures.

## Visual demo

The checked-in static twin is at [`demo/type111/`](../../demo/type111/). Regenerate replay metadata using its documented exporter; serve the directory locally to inspect it. The schematic remains synthetic and does not display Honda-carried video.

## Boundaries

Run only scoped, reviewed live milestones. Do not use a test command to stage or deploy artifacts. See [CONTRIBUTING.md](../../CONTRIBUTING.md) and [current next action](../../NEXT_ACTION.md).
