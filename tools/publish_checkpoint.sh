#!/bin/sh
set -eu
repo=$(git rev-parse --show-toplevel)
exec python3 "$repo/tools/publish_checkpoint.py" --repo "$repo" "$@"
