#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
: "${ANDROID_HOME:?Set ANDROID_HOME to an Android SDK with platforms/android-17/android.jar}"
jar="$ANDROID_HOME/platforms/android-17/android.jar"
[ -f "$jar" ] || { echo "Missing API17 android.jar: $jar" >&2; exit 2; }
out="$repo/build/r7c/java-api17"
rm -rf "$out"
mkdir -p "$out"
find "$repo/android/src/main/java" -name '*.java' -print > "$repo/build/r7c/java-sources.txt"
javac -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$jar" -d "$out" @"$repo/build/r7c/java-sources.txt"
jar cf "$repo/build/r7c/claritylink-android-api17.jar" -C "$out" .
echo "Compiled API17 adapter classes to $out"
