"""Generate FDR refinement verdicts for the archived AUV behaviour models.

Produces `malcom.evaluation/fdr_results.json` — the per-run refinement
verdicts that back the paper's behaviour-verification claims — by running the
pipeline's OWN code path (behaviour_assembly + fdr4), so the verdicts carry
production semantics, including the distinction between verified, failed, and
unverified-because-the-tool-could-not-run.

Requires a licensed FDR4 (run `refines` once interactively to license it) and
the built MALCOMj distribution (MALCOMj/build/install). Run via the wrapper:

    ./scripts/run_fdr_verdicts.sh
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "MALCOMp"))

import behaviour_assembly  # noqa: E402
import fdr4  # noqa: E402

FDR_CONFIG = {
    "enabled": True,
    "robochart_gen_dir": str(REPO / "MALCOMj" / "lib" / "robochart"),
    "fdr4_path": "/Applications/FDR4.app/Contents/MacOS/refines",
    "timeout": 600,
}

OUT = REPO / "malcom.evaluation" / "fdr_results.json"
WORK = REPO / "malcom.evaluation" / "fdr_work"


def main() -> int:
    runs = sorted((REPO / "case_studies" / "auv" / "output" / "runs").glob("web_*"))
    if not runs:
        print("no archived runs found", file=sys.stderr)
        return 1
    WORK.mkdir(parents=True, exist_ok=True)

    results = {}
    for run in runs:
        stm = run / "STM.txt"
        entry: dict = {"run": run.name, "stm": str(stm.relative_to(REPO))}
        if not stm.is_file():
            entry["status"] = "no behaviour model in run directory"
            results[run.name] = entry
            continue

        rct = WORK / f"{run.name}_complete.rct"
        t0 = time.time()
        assembled = behaviour_assembly.assemble_complete_rct(stm, rct)
        entry["assembled"] = bool(assembled)
        if not assembled:
            # The archived model does not parse as RoboChart (the assembler
            # surfaces the official parser's error). Record honestly: this
            # model was never FDR-checkable in its archived form.
            entry["status"] = "assembly failed: archived model does not parse as RoboChart"
            results[run.name] = entry
            continue

        chk = fdr4.run_fdr4_check(rct, config=FDR_CONFIG)
        entry.update({
            "check": chk.name,
            "ok": bool(chk.ok),
            "unverified": bool(chk.unverifiable),
            "detail": chk.detail or "",
            "seconds": round(time.time() - t0, 1),
        })
        entry["status"] = ("verified" if chk.ok
                           else "unverified (tool could not run)" if chk.unverifiable
                           else "FAILED")
        results[run.name] = entry
        print(f"  {run.name}: {entry['status']} — {entry.get('detail','')[:80]}")

    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fdr": FDR_CONFIG["fdr4_path"],
        "note": ("Refinement verdicts for the archived May 2026 AUV runs, "
                 "produced by the pipeline's own gate (MALCOMp/fdr4.py). "
                 "Runs whose archived behaviour model does not parse as "
                 "RoboChart are recorded as assembled=false rather than "
                 "skipped silently."),
        "runs": results,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(REPO)}")

    n_ok = sum(1 for r in results.values() if r.get("ok"))
    n_unv = sum(1 for r in results.values() if r.get("unverified"))
    n_bad = sum(1 for r in results.values() if r.get("assembled") is False)
    print(f"summary: {n_ok} verified, {n_unv} unverified, "
          f"{n_bad} not assemblable, of {len(results)} runs")
    # Exit nonzero if nothing was actually verified — likely licence problem.
    return 0 if n_ok > 0 or n_bad == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
