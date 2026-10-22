#!/usr/bin/env bash
# Build a source-identified CL-R12 renderer A/B pair.
#
#   baseline  = the tree at <baseline_ref> (renderer, build script, everything) with
#               ONLY the performance activity taken from the candidate (HEAD)
#   candidate = HEAD
#
# Both variants therefore run the same workload code and differ in the renderer
# (and its build script) alone, which is the change under test. Both are signed
# with one shared keystore so the baseline can be replaced by the candidate on the
# same emulator. Nothing in the candidate checkout is modified, and the baseline
# is built in a separate detached worktree that is removed afterwards.
#
# usage: build_cl_r12_renderer_ab.sh <baseline_ref> <fresh_output_dir>
# The output directory must not exist (the underlying build script refuses reuse).
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
baseline_ref="${1:?baseline ref required}"
out="${2:?fresh output directory required}"
case "$out" in /*) ;; *) out="$repo/$out" ;; esac
[[ ! -e "$out" ]] || { echo "Output directory must not exist: $out" >&2; exit 2; }

if [[ -n "$(git -C "$repo" status --porcelain --untracked-files=no)" ]]; then
  echo 'Refusing to build an A/B pair from a tracked-modified checkout.' >&2
  exit 3
fi
baseline_sha="$(git -C "$repo" rev-parse --verify "$baseline_ref^{commit}")"
candidate_sha="$(git -C "$repo" rev-parse HEAD)"
[[ "$baseline_sha" != "$candidate_sha" ]] || { echo 'Baseline and candidate are the same commit.' >&2; exit 4; }
git -C "$repo" merge-base --is-ancestor "$baseline_sha" "$candidate_sha" || {
  echo 'Baseline must be an ancestor of the candidate.' >&2; exit 4; }

activity='android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java'
renderer_dir='src/claritylink-renderer/android-api17'
mkdir -p "$out"
work="$(mktemp -d /tmp/cl-r12-ab-XXXXXX)"
trap 'git -C "$repo" worktree remove --force "$work/baseline" >/dev/null 2>&1 || true; rm -rf "$work"' EXIT

git -C "$repo" worktree add --detach "$work/baseline" "$baseline_sha" >/dev/null
git -C "$repo" show "HEAD:$activity" > "$work/baseline/$activity"
# The workload must be the candidate's, including helper classes it uses that the baseline tree
# predates. Overlay those files and register them in the baseline's explicit source list, so the
# only thing that differs between the arms is the renderer.
overlay=()
for helper in android/src/main/java/org/claritylink/android/SyntheticFrameFill.java; do
  if git -C "$repo" cat-file -e "HEAD:$helper" 2>/dev/null && ! git -C "$repo" cat-file -e "$baseline_sha:$helper" 2>/dev/null; then
    mkdir -p "$(dirname "$work/baseline/$helper")"
    git -C "$repo" show "HEAD:$helper" > "$work/baseline/$helper"
    python3 - "$work/baseline/tools/build_cl_imp_03_apks.sh" "$helper" <<'PY'
import sys
path, helper = sys.argv[1:3]
text = open(path).read()
anchor = '  "$repo/android/src/main/java/org/claritylink/android/Yuv420FrameAdapter.java" \\\n'
line = '  "$repo/' + helper + '" \\\n'
if line in text:
    sys.exit(0)
if anchor not in text:
    sys.exit("baseline build script has no insertion anchor for the workload helper")
open(path, "w").write(text.replace(anchor, anchor + line, 1))
PY
    overlay+=("$helper")
  fi
done

tree_digest() {  # stable digest of a directory of tracked files at a given worktree
  (cd "$1" && git ls-files -s -- "$renderer_dir" | sha256sum | awk '{print $1}')
}

# The build script writes into repo/build or /tmp only; use a /tmp campaign dir.
base_build="/tmp/cl-imp-03-r12-baseline-$$"
cand_build="/tmp/cl-imp-03-r12-candidate-$$"
CL_IMP_03_BUILD_DIR="$base_build" "$work/baseline/tools/build_cl_imp_03_apks.sh" >"$out/build-baseline.txt"
shared_keystore="$base_build/cl-imp-03-debug.keystore"
CL_IMP_03_BUILD_DIR="$cand_build" CL_IMP_03_KEYSTORE="$shared_keystore" \
  "$repo/tools/build_cl_imp_03_apks.sh" >"$out/build-candidate.txt"

cp "$base_build/claritylink-display-lab.apk" "$out/baseline.apk"
cp "$cand_build/claritylink-display-lab.apk" "$out/candidate.apk"
if cmp -s "$out/baseline.apk" "$out/candidate.apk"; then
  echo 'Baseline and candidate APKs are byte-identical; refusing to report an A/B result.' >&2
  exit 9
fi

base_activity_sha="$(sha256sum "$work/baseline/$activity" | awk '{print $1}')"
cand_activity_sha="$(sha256sum "$repo/$activity" | awk '{print $1}')"
[[ "$base_activity_sha" == "$cand_activity_sha" ]] || { echo 'Workload source differs between variants.' >&2; exit 5; }

{
  echo "baseline_ref=$baseline_ref"
  echo "baseline_commit=$baseline_sha"
  echo "candidate_commit=$candidate_sha"
  echo "ab_mode=renderer"
  echo "workload_overlay_files=${overlay[*]:-none}"
  echo "workload_activity_sha256=$cand_activity_sha"
  echo "baseline_renderer_tree_sha256=$(tree_digest "$work/baseline")"
  echo "candidate_renderer_tree_sha256=$(tree_digest "$repo")"
  echo "baseline_build_script_sha256=$(sha256sum "$work/baseline/tools/build_cl_imp_03_apks.sh" | awk '{print $1}')"
  echo "candidate_build_script_sha256=$(sha256sum "$repo/tools/build_cl_imp_03_apks.sh" | awk '{print $1}')"
  echo "baseline_apk_sha256=$(sha256sum "$out/baseline.apk" | awk '{print $1}')"
  echo "candidate_apk_sha256=$(sha256sum "$out/candidate.apk" | awk '{print $1}')"
  echo "files_differing_baseline_to_candidate:"
  git -C "$repo" diff --name-only "$baseline_sha" "$candidate_sha" -- android src tools | sed 's/^/  /'
} > "$out/ab-identity.txt"
cat "$out/ab-identity.txt"
echo "CL_R12_RENDERER_AB_BUILT baseline=$out/baseline.apk candidate=$out/candidate.apk"
