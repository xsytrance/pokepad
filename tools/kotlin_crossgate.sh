#!/usr/bin/env bash
# Compile the Kotlin engine and validate it against the Python-generated fixture.
# Uses the Kotlin compiler bundled in the local Gradle distribution (no SDK/Android).
set -euo pipefail
cd "$(dirname "$0")/.."

JAVA_HOME=${JAVA_HOME:-/home/xsyprime/.gradle/jdks/eclipse_adoptium-17-amd64-linux.2}
LIB=$(ls -d /home/xsyprime/.gradle/wrapper/dists/gradle-9.6.1-bin/*/gradle-9.6.1/lib | head -1)
STDLIB="$LIB/kotlin-stdlib-2.3.21.jar"
OUT=build/kotlin
mkdir -p "$OUT"

echo "· compiling kotlin/Engine.kt kotlin/CrossGate.kt"
"$JAVA_HOME/bin/java" -cp "$LIB/*" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
    kotlin/Engine.kt kotlin/CrossGate.kt -classpath "$STDLIB" -d "$OUT/crossgate.jar" 2>&1 | grep -viE "warning:|experimental" || true

echo "· running cross-gate against fixtures/crossgate.tsv"
"$JAVA_HOME/bin/java" -cp "$OUT/crossgate.jar:$STDLIB" CrossGateKt fixtures/crossgate.tsv
