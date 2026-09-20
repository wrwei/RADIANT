"""Score the RQ2 control arms: single vs single_repair vs multi.

The paper's RQ2 compares the full cooperating pipeline against a single-pass
baseline that has neither checking nor repair, so it measures role
decomposition and iterative repair together. The `single_repair` arm adds the
gate and repair loop to the single generator, giving two clean contrasts:

    multi         vs single_repair   isolates role decomposition
    single_repair vs single          isolates iterative repair

For each run this recomputes the phase gate with the real MALCOMj runner
(rather than trusting whatever was recorded during the run) and reads token
usage from the run's own tokens.json. Fisher's exact test compares pass rates;
it is used rather than a chi-square because the counts are small.

Usage:
    export MALCOMJ_RUNNER=/path/to/MALCOMj/build/install/MALCOMj/bin/MALCOMj
    python malcom.evaluation/metrics/rq2_control/analyse.py \
        --root case_studies/auv/output/rq2_10rep/deepseek_v4 --stage model
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from math import comb
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "MALCOMp"))

import verification as V  # noqa: E402

ARMS = ("single", "single_repair", "multi")
# The structural check for each phase — the one the repair loop can act on.
STRUCTURAL = {"model": "eol_executes", "dsml": "emfatic_valid",
              "behaviour": "robochart_parses", "concept": "schema"}


def fisher_exact_2x2(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher's exact p for [[a,b],[c,d]] (pure stdlib).

    Sums the hypergeometric probability of every table with the same margins
    whose probability is no greater than the observed one.
    """
    n = a + b + c + d
    r1, r2 = a + b, c + d
    c1 = a + c
    if not n or not c1 or c1 == n or not r1 or not r2:
        return 1.0

    def p_table(x):
        return (comb(r1, x) * comb(r2, c1 - x)) / comb(n, c1)

    lo = max(0, c1 - r2)
    hi = min(r1, c1)
    p_obs = p_table(a)
    return min(1.0, sum(p_table(x) for x in range(lo, hi + 1)
                        if p_table(x) <= p_obs + 1e-12))


def score_run(run_dir: Path, stage: str, runner: str | None) -> dict | None:
    """Recompute the gate and read tokens for one run directory."""
    if not run_dir.is_dir():
        return None
    res = V.verify(stage, run_dir, malcomj_runner=runner)
    key = STRUCTURAL.get(stage)
    check = next((c for c in res.checks if c.name == key), None)
    tok = {}
    tp = run_dir / "tokens.json"
    if tp.is_file():
        try:
            tok = json.loads(tp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            tok = {}
    # Repair cost is booked differently per arm, and the difference matters when
    # comparing columns. The single-agent arms call the model directly, so
    # run_stage_single_agent_with_repair records repair separately under
    # "<stage>_repair". The multi arm's usage comes from AutoGen's
    # gather_usage_summary, which aggregates the WHOLE group chat — repair agent
    # included — into the one "<stage>" entry. So for multi, `gen_tokens` is
    # really generation+repair and `repair_tokens` is 0 by construction, not
    # because no repair happened. Only `total_tokens` is comparable across arms.
    gen = tok.get(stage, {})
    rep = tok.get(f"{stage}_repair", {})

    def total(d):
        return int(d.get("input_tokens", 0)) + int(d.get("output_tokens", 0))

    return {
        "run": run_dir.name,
        "structural_check": key,
        "passed": bool(check and check.ok),
        "unverified": bool(check and check.unverifiable),
        "detail": ((check.detail or "").splitlines() or [""])[0][:120] if check else "",
        "gate_passed": res.passed,
        "fully_verified": res.fully_verified,
        "gen_tokens": total(gen),
        "repair_tokens": total(rep),
        "total_tokens": total(gen) + total(rep),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True,
                    help="directory containing <arm>/run_NNN/ subdirectories")
    ap.add_argument("--stage", default="model", choices=sorted(STRUCTURAL))
    ap.add_argument("--runner", default=os.environ.get("MALCOMJ_RUNNER"),
                    help="MALCOMj launcher (default: $MALCOMJ_RUNNER)")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if args.runner is None:
        print("WARNING: no MALCOMj runner given; the structural check will "
              "report UNVERIFIED and the comparison will not discriminate.",
              file=sys.stderr)

    per_run: dict[str, list[dict]] = {}
    for arm in ARMS:
        rows = []
        for d in sorted((root / arm).glob("run_*")):
            # A run directory's PATH is not its identity: prefer the manifest
            # the sweep stamps (run_manifest.json), and refuse to score a run
            # under an arm directory whose manifest names a different arm —
            # that is another experiment's data, not this arm's.
            mf = d / "run_manifest.json"
            if mf.is_file():
                try:
                    owner = json.loads(mf.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as ex:
                    print(f"ERROR: unreadable manifest {mf}: {ex} — run skipped",
                          file=sys.stderr)
                    continue
                if owner.get("variant") != arm:
                    print(f"ERROR: {d} manifest says variant="
                          f"{owner.get('variant')!r} but it sits under {arm!r} "
                          f"— cross-arm contamination, run skipped",
                          file=sys.stderr)
                    continue
            else:
                print(f"note: {d} has no run_manifest.json (pre-manifest run); "
                      f"arm inferred from its path", file=sys.stderr)
            r = score_run(d, args.stage, args.runner)
            if r:
                r["arm"] = arm
                rows.append(r)
        per_run[arm] = rows

    summary = []
    for arm in ARMS:
        rows = per_run[arm]
        if not rows:
            continue
        n = len(rows)
        npass = sum(r["passed"] for r in rows)
        nunver = sum(r["unverified"] for r in rows)
        gen = [r["gen_tokens"] for r in rows]
        rep = [r["repair_tokens"] for r in rows]
        tot = [r["total_tokens"] for r in rows]
        summary.append({
            "arm": arm, "n": n, "passed": npass,
            "pass_rate": npass / n,
            "unverified": nunver,
            "repaired_runs": sum(1 for x in rep if x > 0),
            "gen_tokens_mean": sum(gen) / n,
            "repair_tokens_mean": sum(rep) / n,
            "total_tokens_mean": sum(tot) / n,
        })

    def rate(arm):
        s = next((x for x in summary if x["arm"] == arm), None)
        return (s["passed"], s["n"] - s["passed"]) if s else (0, 0)

    contrasts = []
    for hi, lo, what in (("single_repair", "single", "iterative repair"),
                         ("multi", "single_repair", "role decomposition"),
                         ("multi", "single", "both combined")):
        a, b = rate(hi)
        c, d = rate(lo)
        if (a + b) and (c + d):
            contrasts.append({
                "contrast": f"{hi} vs {lo}", "isolates": what,
                "pass_hi": f"{a}/{a+b}", "pass_lo": f"{c}/{c+d}",
                "p_fisher": round(fisher_exact_2x2(a, b, c, d), 4),
            })

    out = Path(args.out_dir) if args.out_dir else \
        REPO / "malcom.evaluation" / "metrics" / "results" / "rq2_control"
    out.mkdir(parents=True, exist_ok=True)
    flat = [r for arm in ARMS for r in per_run[arm]]
    if flat:
        with (out / "rq2_per_run.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(flat[0]))
            w.writeheader()
            w.writerows(flat)
    if summary:
        with (out / "rq2_summary.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(summary[0]))
            w.writeheader()
            w.writerows(summary)
    if contrasts:
        with (out / "rq2_contrasts.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(contrasts[0]))
            w.writeheader()
            w.writerows(contrasts)

    print(f"stage: {args.stage}  |  structural check: {STRUCTURAL[args.stage]}")
    print(f"{'arm':16}{'n':>3}{'pass':>7}{'rate':>8}{'unver':>7}"
          f"{'repaired':>10}{'gen tok':>10}{'repair tok':>12}{'total':>10}")
    note = ("  note: the multi arm books repair inside its generation "
            "total (AutoGen aggregates the whole group chat), so its "
            "'repair tok' is 0 by construction, not because no repair "
            "happened. Only 'total' is comparable across arms.")
    for s in summary:
        print(f"{s['arm']:16}{s['n']:>3}{s['passed']:>7}{s['pass_rate']:>8.2f}"
              f"{s['unverified']:>7}{s['repaired_runs']:>10}"
              f"{s['gen_tokens_mean']:>10,.0f}{s['repair_tokens_mean']:>12,.0f}"
              f"{s['total_tokens_mean']:>10,.0f}")
    print(note)
    print()
    for c in contrasts:
        print(f"  {c['contrast']:32} isolates {c['isolates']:20} "
              f"{c['pass_hi']} vs {c['pass_lo']}  Fisher p={c['p_fisher']}")
    print(f"\nwrote {out}/rq2_per_run.csv, rq2_summary.csv, rq2_contrasts.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
