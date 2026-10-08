#!/usr/bin/env bash
# Runs the ORIGINAL Java RL agent (default config: readQ=true, Qindex=20) headless for N games
# in a scratch copy of the repo, so nothing in the repo is modified.
# Output: results/reference/java_legacy.json  (per-game score / steps / died)
set -euo pipefail
N=${1:-150}
REPO=$(cd "$(dirname "$0")/../.." && pwd)
TMP=$(mktemp -d)
cp -r "$REPO/ReinforcementLearning" "$REPO/Images" "$REPO/data" "$TMP/"
cp "$REPO/python/scripts/java_harness/Harness.java" "$TMP/ReinforcementLearning/"
rm -f "$TMP/data/StepReward.txt"
cd "$TMP"
javac -d out ReinforcementLearning/*.java
java -Djava.awt.headless=true -cp out ReinforcementLearning.Harness "$N" > run.log
python3 - "$REPO/results/reference/java_legacy.json" <<'PY'
import json, re, sys
score = [int(x) for x in open("Score.txt")]
steps = [int(x) for x in re.findall(r"Step used: (\d+)", open("run.log").read())]
recs = [{"score": sc, "steps": st, "died": st < 1000 and sc < 377} for sc, st in zip(score, steps)]
json.dump({"agent": "java-legacy (original code, readQ, Qindex=20)", "records": recs}, open(sys.argv[1], "w"), indent=1)
print(len(recs), "games written to", sys.argv[1])
PY
rm -rf "$TMP"
