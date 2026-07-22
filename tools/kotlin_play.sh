#!/usr/bin/env bash
# Compile and run the full Kotlin battle engine (demo + self-test).
set -euo pipefail
cd "$(dirname "$0")/.."
JAVA_HOME=${JAVA_HOME:-/home/xsyprime/.gradle/jdks/eclipse_adoptium-17-amd64-linux.2}
LIB=$(ls -d /home/xsyprime/.gradle/wrapper/dists/gradle-9.6.1-bin/*/gradle-9.6.1/lib | head -1)
STDLIB="$LIB/kotlin-stdlib-2.3.21.jar"
OUT=build/kotlin; mkdir -p "$OUT"
echo "· compiling kotlin/Engine.kt kotlin/Battle.kt"
"$JAVA_HOME/bin/java" -cp "$LIB/*" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
    kotlin/Engine.kt kotlin/Battle.kt -classpath "$STDLIB" -d "$OUT/battle.jar" 2>&1 | grep -viE "warning:|experimental" || true
echo "· running"
"$JAVA_HOME/bin/java" -cp "$OUT/battle.jar:$STDLIB" BattleKt
