#!/bin/bash
# Generate the FDR refinement verdicts (malcom.evaluation/fdr_results.json)
# for the archived AUV runs. Run this in a normal macOS terminal:
#
#     cd /Users/ranwei/Git/REMEDIATE
#     ./scripts/run_fdr_verdicts.sh
#
# Step 0 (once): FDR must be licensed. If you haven't yet, the script detects
# it and drops you into the interactive licence prompt first (option 2 =
# academic licence). Everything else is automatic.
set -euo pipefail
cd "$(dirname "$0")/.."

REFINES=/Applications/FDR4.app/Contents/MacOS/refines
JVM=/Users/ranwei/.claude-science/conda/envs/radiant-audit/lib/jvm

# --- 0. preflight -----------------------------------------------------------
[ -x "$REFINES" ] || { echo "FDR4 not found at $REFINES"; exit 1; }

if [ -d "$JVM" ]; then
  export JAVA_HOME="$JVM"
elif /usr/libexec/java_home -v 17+ >/dev/null 2>&1; then
  export JAVA_HOME="$(/usr/libexec/java_home -v 17+)"
else
  echo "No JDK 17+ found. Install one (e.g. brew install openjdk) and retry."; exit 1
fi
echo "JAVA_HOME=$JAVA_HOME"

if [ ! -d MALCOMj/build/install/MALCOMj/lib ]; then
  echo "MALCOMj is not built (MALCOMj/build/install missing)."
  echo "Build it first: cd MALCOMj && gradle installDist -PjavaVersion=21"
  exit 1
fi

# --- 1. licence check (interactive on first run) ----------------------------
# Unlicensed refines says "A valid license is required" / "license is invalid"
# or prompts "Select an option". A LICENSED run prints a banner containing
# "License: Academic license ..." — so match the failure phrases specifically,
# not the bare word "license".
TMPCSP=$(mktemp -t lictest).csp
echo 'assert SKIP :[deadlock-free]' > "$TMPCSP"   # SKIP is deadlock-free: expect a pass
unlicensed() {
  "$REFINES" --format framed_json "$TMPCSP" 2>&1 | \
    grep -qiE "valid license is required|license is invalid|Select an option"
}
if unlicensed; then
  echo
  echo ">>> FDR is not licensed on this machine. Answer its prompts once"
  echo ">>> (option 2 = academic licence), then the verdicts run starts."
  echo
  "$REFINES" "$TMPCSP" || true
  if unlicensed; then
    echo "Licence still not recorded — aborting."; rm -f "$TMPCSP"; exit 1
  fi
fi
rm -f "$TMPCSP"
echo "FDR licence OK."

# --- 2. run the verdicts ----------------------------------------------------
# Uses the pipeline's own gate code; writes malcom.evaluation/fdr_results.json
python3 scripts/fdr_verdicts.py
echo
echo "Done. Review malcom.evaluation/fdr_results.json, then commit it:"
echo "  git add malcom.evaluation/fdr_results.json scripts/"
echo "  git commit -m 'data: FDR refinement verdicts for the archived AUV runs'"
