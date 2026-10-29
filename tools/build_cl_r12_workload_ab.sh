#!/usr/bin/env bash
# Build a CL-R12 *workload* A/B pair: the renderer and everything else are identical (HEAD);
# only the performance Activity differs.
#
#   baseline  = HEAD with MessengerFramePerformanceActivity.java taken from <baseline_ref>
#   candidate = HEAD
#
# Use it to measure a change to the synthetic producer inside one CI run. The renderer-isolating
# pair (build_cl_r12_renderer_ab.sh) answers a different question and must not be mixed with this
# one: record which mode produced a result. Both arms share one keystore.
#
# usage: build_cl_r12_workload_ab.sh <baseline_ref> <fresh_output_dir>
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
baseline_ref="${1:?baseline ref required}"
out="${2:?fresh output directory required}"
case "$out" in /*) ;; *) out="$repo/$out" ;; esac
[[ ! -e "$out" ]] || { echo "Output directory must not exist: $out" >&2; exit 2; }
if [[ -n "$(git -C "$repo" status --porcelain --untracked-files=no)" ]]; then
  echo 'Refusing to build an A/B pair from a tracked-modified checkout.' >&2; exit 3
fi
baseline_sha="$(git -C "$repo" rev-parse --verify "$baseline_ref^{commit}")"
candidate_sha="$(git -C "$repo" rev-parse HEAD)"
activity='android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java'
git -C "$repo" cat-file -e "$baseline_sha:$activity" || { echo 'Baseline ref has no performance Activity.' >&2; exit 4; }
mkdir -p "$out"
work="$(mktemp -d /tmp/cl-r12-wab-XXXXXX)"
trap 'git -C "$repo" worktree remove --force "$work/baseline" >/dev/null 2>&1 || true; rm -rf "$work"' EXIT

git -C "$repo" worktree add --detach "$work/baseline" "$candidate_sha" >/dev/null
git -C "$repo" show "$baseline_sha:$activity" > "$work/baseline/$activity"

base_build="/tmp/cl-imp-03-r12w-baseline-$$"
cand_build="/tmp/cl-imp-03-r12w-candidate-$$"
CL_IMP_03_BUILD_DIR="$base_build" "$work/baseline/tools/build_cl_imp_03_apks.sh" >"$out/build-baseline.txt"
CL_IMP_03_BUILD_DIR="$cand_build" CL_IMP_03_KEYSTORE="$base_build/cl-imp-03-debug.keystore" \
  "$repo/tools/build_cl_imp_03_apks.sh" >"$out/build-candidate.txt"
cp "$base_build/claritylink-display-lab.apk" "$out/baseline.apk"
cp "$cand_build/claritylink-display-lab.apk" "$out/candidate.apk"
if cmp -s "$out/baseline.apk" "$out/candidate.apk"; then
  echo 'Baseline and candidate APKs are byte-identical; refusing to report an A/B result.' >&2; exit 9
fi
{
  echo "ab_mode=workload"
  echo "baseline_activity_ref=$baseline_ref"
  echo "baseline_activity_commit=$baseline_sha"
  echo "candidate_commit=$candidate_sha"
  echo "baseline_activity_sha256=$(sha256sum "$work/baseline/$activity" | awk '{print $1}')"
  echo "candidate_activity_sha256=$(sha256sum "$repo/$activity" | awk '{print $1}')"
  echo "renderer_tree_sha256_both=$(cd "$repo" && git ls-files -s -- src/claritylink-renderer/android-api17 | sha256sum | awk '{print $1}')"
  echo "baseline_apk_sha256=$(sha256sum "$out/baseline.apk" | awk '{print $1}')"
  echo "candidate_apk_sha256=$(sha256sum "$out/candidate.apk" | awk '{print $1}')"
} > "$out/ab-identity.txt"
cat "$out/ab-identity.txt"
echo "CL_R12_WORKLOAD_AB_BUILT baseline=$out/baseline.apk candidate=$out/candidate.apk"
