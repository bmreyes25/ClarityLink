#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
"$repo/tools/compile_android_api17_java.sh"
jar="$ANDROID_HOME/platforms/android-17/android.jar"
out="$repo/build/r7c/java-api17"
mkdir -p "$out/test"
"${JAVAC:-javac}" -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$jar" -classpath "$out" \
  -d "$out/test" "$repo/android/src/test/java/org/claritylink/android/OfflinePolicyTest.java"
"${JAVA:-java}" -cp "$out/test:$out" org.claritylink.android.OfflinePolicyTest
