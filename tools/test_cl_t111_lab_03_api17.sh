#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
java_home=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
java="$java_home/bin/java"
javac="$java_home/bin/javac"
[ -x "$java" ] && [ -x "$javac" ] || { echo 'Pinned Temurin 17 toolchain unavailable.' >&2; exit 2; }
out=$(mktemp -d "${TMPDIR:-/tmp}/cl-t111-lab-03-test.XXXXXX")
trap 'rm -rf "$out"' EXIT HUP INT TERM
"$javac" -source 1.7 -target 1.7 -Xlint:all -d "$out" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameStreamIdentity.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameIpcProtocol.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/NegotiatedType111Lifecycle.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Type111ControlPlane.java" \
  "$repo/android/src/test/java/org/claritylink/android/NegotiatedType111LifecycleTest.java"
"$java" -cp "$out" org.claritylink.android.NegotiatedType111LifecycleTest
