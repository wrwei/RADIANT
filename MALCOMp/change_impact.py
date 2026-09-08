"""Change-impact analysis over the pipeline's traceability JSONs.

Consumes all four phase trace files (concept/dsml/model/behaviour), keeps a baseline
of per-requirement content hashes, and reports which model elements across Phases 2-5
are impacted when requirements change. Deterministic, no LLM.

CLI:
    python change_impact.py snapshot   # capture the baseline (output/cia_baseline.json)
    python change_impact.py report     # diff requirements vs baseline -> impact report

Exit codes (report): 0 = no changes, 3 = changes detected, 2 = no baseline yet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Link:
    gid: str            # canonicalised requirement id
    phase: str          # concept | dsml | model | behaviour
    element: str        # human-readable element label
    source: dict        # {file, line_start, line_end, resolved}


def _canonical_gid(value) -> str:
    if value is None:
        return ""
    return re.sub(r"[^0-9a-z]+", "", str(value).strip().casefold())


def _hash(text) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


# --- per-phase trace specs --------------------------------------------------

def _concept_label(e):
    concept = str(e.get("Concept") or "").strip()
    instance = str(e.get("Instance") or "").strip()
    if concept and instance:
        return f"{concept}: {instance}"
    return concept or instance or "?"


def _dsml_label(e):
    return str(e.get("Emfatic_class") or "?").strip()


def _model_label(e):
    elem = str(e.get("Model_Element") or "").strip()
    eid = str(e.get("Model_Element_id") or "").strip()
    return f"{elem}: {eid}" if elem and eid else (elem or eid or "?")


def _behaviour_label(e):
    t = str(e.get("transition") or "?").strip()
    src = str(e.get("source_state") or "").strip()
    dst = str(e.get("end_state") or "").strip()
    return f"{t} ({src} -> {dst})" if src and dst else t


# (phase, filename, current tag, legacy tags, label builder). The legacy tags let
# this tool read trace files written by earlier versions of the pipeline (the
# concept phase emitted "req" before it was renamed "term_trace"); a legacy hit is
# logged so stale artefacts are visible rather than silently contributing nothing.
_TRACE_SPECS = [
    ("concept", "result_concept_trace.json", "term_trace", ("req",), _concept_label),
    ("dsml", "result_dsml_trace.json", "dsl_trace", (), _dsml_label),
    ("model", "result_model_trace.json", "model_trace", (), _model_label),
    ("behaviour", "result_behaviour_trace.json", "stm_trace", (), _behaviour_label),
]


def _trace_entries(data: dict, tag: str, legacy: tuple, fname: str) -> list:
    """Entries under `tag`, falling back to any `legacy` tag with a warning."""
    if not isinstance(data, dict):
        return []
    if isinstance(data.get(tag), list):
        return data[tag]
    for old in legacy:
        if isinstance(data.get(old), list):
            logger.warning(
                "%s uses the legacy trace tag %r (current: %r) — this artefact "
                "predates the current pipeline; regenerate it.", fname, old, tag)
            return data[old]
    return []


def load_links(output_dir) -> list[Link]:
    """Parse the four phase trace JSONs in `output_dir` into Links. Missing or
    unparseable files are skipped (a phase may not have run)."""
    out = Path(output_dir)
    links: list[Link] = []
    for phase, fname, tag, legacy, labeller in _TRACE_SPECS:
        p = out / fname
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as ex:
            logger.warning("skipping %s: %s", fname, ex)
            continue
        for e in _trace_entries(data, tag, legacy, fname):
            if not isinstance(e, dict):
                continue
            gid = _canonical_gid(e.get("GID") or e.get("requirement_gid"))
            if not gid:
                continue
            links.append(Link(gid, phase, labeller(e), e.get("source") or {}))
    return links


def _requirement_items(data, fname: str) -> list:
    """The requirements array from a requirement file.

    Reads the documented ``requirements`` key rather than "whichever value
    happens to be a list", so adding an unrelated list-valued key (metadata,
    tags) cannot silently make the tool read the wrong array.
    """
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("requirements"), list):
        return data["requirements"]
    fallback = next((k for k, v in data.items() if isinstance(v, list)), None)
    if fallback is None:
        logger.warning("%s has no 'requirements' array; ignoring it", fname)
        return []
    logger.warning("%s has no 'requirements' key; falling back to %r", fname, fallback)
    return data[fallback]


def load_requirements(case_dir) -> dict:
    """Map canonical GID -> requirement description, merged across the architecture
    and behaviour requirement files."""
    reqs: dict[str, str] = {}
    rd = Path(case_dir) / "requirements"
    for fname in ("requirement_architecture.json", "requirement_behaviour.json"):
        p = rd / fname
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as ex:
            logger.warning("skipping %s: %s", fname, ex)
            continue
        items = _requirement_items(data, fname)
        for r in items:
            if not isinstance(r, dict):
                continue
            raw = r.get("gid") or r.get("GID") or r.get("id") or r.get("name")
            gid = _canonical_gid(raw)
            if not gid:
                continue
            # Canonicalisation folds case and strips punctuation, so distinct raw
            # ids can collide ("LRE-Beh6" / "lre_beh_6"). Silently overwriting
            # would drop a requirement from every downstream impact set.
            if gid in reqs and reqs[gid] != r.get("description", ""):
                logger.warning(
                    "requirement id collision: %r canonicalises to %r, which is "
                    "already used by another requirement; keeping the first and "
                    "IGNORING this one. Disambiguate the requirement ids.",
                    raw, gid)
                continue
            reqs[gid] = r.get("description", "")
    return reqs


def build_graph(links) -> dict:
    """Index links by requirement GID."""
    graph: dict[str, list[Link]] = {}
    for l in links:
        graph.setdefault(l.gid, []).append(l)
    return graph


def _link_dict(l: Link) -> dict:
    # Flatten the verified source span as-is: line phases carry line_start/line_end,
    # the concept phase carries char_start/char_end. Both keep file + resolved.
    return {"phase": l.phase, "element": l.element, **(l.source or {})}


def snapshot(requirements, links, created=None) -> dict:
    """A baseline: per-requirement content hashes + the trace links at this point."""
    return {
        "created": created,
        "requirements": {gid: _hash(text) for gid, text in requirements.items()},
        "links": [_link_dict(l) | {"gid": l.gid} for l in links],
    }


def diff(baseline, current_requirements) -> dict:
    """Compare current requirement hashes against the baseline."""
    base = baseline.get("requirements", {}) if isinstance(baseline, dict) else {}
    cur = {gid: _hash(text) for gid, text in current_requirements.items()}
    changed = sorted(g for g in cur if g in base and cur[g] != base[g])
    added = sorted(g for g in cur if g not in base)
    removed = sorted(g for g in base if g not in cur)
    return {"changed": changed, "added": added, "removed": removed}


def impact(diff_result, graph, requirements) -> dict:
    """Build the impact report from a diff and the trace graph."""
    changed_reqs, affected_count = [], 0
    for gid in diff_result.get("changed", []):
        affected = [_link_dict(l) for l in graph.get(gid, [])]
        affected_count += len(affected)
        changed_reqs.append({"gid": gid, "text": requirements.get(gid, ""), "affected": affected})
    added_reqs = [
        {"gid": gid, "text": requirements.get(gid, ""), "note": "not yet modelled"}
        for gid in diff_result.get("added", [])
    ]
    removed_reqs = [
        {"gid": gid, "orphaned_elements": [_link_dict(l) for l in graph.get(gid, [])]}
        for gid in diff_result.get("removed", [])
    ]
    summary = {
        "changed": len(diff_result.get("changed", [])),
        "added": len(diff_result.get("added", [])),
        "removed": len(diff_result.get("removed", [])),
        "affected_elements": affected_count,
    }
    return {"summary": summary, "changed_requirements": changed_reqs,
            "added_requirements": added_reqs, "removed_requirements": removed_reqs}


def _span(a: dict) -> str:
    if a.get("line_start") is not None:
        return f"{a.get('file')}:{a.get('line_start')}-{a.get('line_end')}"
    if a.get("char_start") is not None:
        return f"{a.get('file')} char {a.get('char_start')}-{a.get('char_end')}"
    return str(a.get("file"))


def _fmt_elem(a: dict) -> str:
    flag = "" if a.get("resolved") else "  (location unverified)"
    return f"    - {a['phase']}: {a['element']}  @ {_span(a)}{flag}"


def format_report(report) -> str:
    s = report["summary"]
    lines = [f"Change impact: {s['changed']} changed, {s['added']} added, "
             f"{s['removed']} removed; {s['affected_elements']} affected element(s)."]
    for ch in report["changed_requirements"]:
        lines.append(f"\n[CHANGED] {ch['gid']}: {ch['text']}")
        if ch["affected"]:
            lines.extend(_fmt_elem(a) for a in ch["affected"])
        else:
            lines.append("    (no model elements traced yet)")
    for ad in report["added_requirements"]:
        lines.append(f"\n[ADDED]   {ad['gid']}: {ad.get('text','')} — {ad.get('note','')}")
    for rm in report["removed_requirements"]:
        lines.append(f"\n[REMOVED] {rm['gid']} — {len(rm['orphaned_elements'])} orphaned element(s)")
        lines.extend(_fmt_elem(a) for a in rm["orphaned_elements"])
    return "\n".join(lines)


# --- thread graph (Digital Thread view) -------------------------------------

_THREAD_PHASES = ["concept", "dsml", "model", "behaviour"]


def _req_nodes(case_dir) -> list:
    """Full requirement set with raw id/name/description + canonical id, merged
    across the architecture and behaviour requirement files (deduped by cid)."""
    nodes, seen = [], set()
    rd = Path(case_dir) / "requirements"
    for fname in ("requirement_architecture.json", "requirement_behaviour.json"):
        p = rd / fname
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        items = _requirement_items(data, fname)
        for r in items:
            if not isinstance(r, dict):
                continue
            rid = str(r.get("id") or r.get("gid") or r.get("GID") or r.get("name") or "")
            cid = _canonical_gid(rid)
            if not cid or cid in seen:
                continue
            seen.add(cid)
            nodes.append({"id": rid or cid, "cid": cid,
                          "name": r.get("name") or rid or cid,
                          "description": r.get("description", "")})
    return nodes


def _load_cia_impact(output_dir):
    """(impacted_cids, impacted_elems) from cia_report.json; empties if absent."""
    p = Path(output_dir) / "cia_report.json"
    cids, elems = set(), set()
    if not p.is_file():
        return cids, elems
    try:
        rep = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return cids, elems
    for key in ("changed_requirements", "added_requirements", "removed_requirements"):
        for entry in rep.get(key, []) if isinstance(rep, dict) else []:
            gid = _canonical_gid(entry.get("gid"))
            if gid:
                cids.add(gid)
            for a in (entry.get("affected") or []) + (entry.get("orphaned_elements") or []):
                elems.add((a.get("phase"), a.get("element")))
    return cids, elems


def build_thread(output_dir, case_dir) -> dict:
    """Assemble the Digital Thread graph: requirement column + per-phase element
    columns + requirement-rooted links, with CIA impact flags."""
    links = load_links(output_dir)
    imp_cids, imp_elems = _load_cia_impact(output_dir)
    linked_cids = {l.gid for l in links}

    req_raw = _req_nodes(case_dir)
    known = {n["cid"] for n in req_raw}
    for gid in sorted(linked_cids - known):           # linked but absent from req files
        req_raw.append({"id": gid, "cid": gid, "name": gid, "description": ""})
    requirement_nodes = [
        {"id": n["id"], "cid": n["cid"], "name": n["name"], "description": n["description"],
         "traced": n["cid"] in linked_cids, "impacted": n["cid"] in imp_cids}
        for n in req_raw
    ]

    nodes = {"requirement": requirement_nodes}
    for p in _THREAD_PHASES:
        nodes[p] = []
    elem_key, out_links = {}, []
    for i, l in enumerate(links):
        k = elem_key.get((l.phase, l.element))
        if k is None:
            k = f"{l.phase}:{len(nodes[l.phase])}"
            elem_key[(l.phase, l.element)] = k
            nodes[l.phase].append({
                "key": k, "label": l.element, "phase": l.phase,
                "impacted": (l.phase, l.element) in imp_elems,
            })
        out_links.append({
            "id": i, "gid": l.gid, "from": l.gid, "phase": l.phase, "to": k,
            "source": l.source or {},
            "impacted": l.gid in imp_cids and (l.phase, l.element) in imp_elems,
        })

    denom = len(requirement_nodes) or 1
    stats = {
        "total_links": len(links),
        "by_phase": {p: len(nodes[p]) for p in _THREAD_PHASES},
        "coverage": {p: round(len({l.gid for l in links if l.phase == p}) / denom, 2)
                     for p in _THREAD_PHASES},
    }
    return {
        "case_study": Path(case_dir).name,
        "columns": ["requirement", *_THREAD_PHASES],
        "nodes": nodes,
        "links": out_links,
        "impact": {"requirements": sorted(imp_cids),
                   "elements": sorted(f"{p}|{e}" for (p, e) in imp_elems if p)},
        "stats": stats,
    }


# --- CLI --------------------------------------------------------------------

def _resolve_paths(args):
    repo_root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config) if args.config else repo_root / "config.yaml"
    cs = args.case_study
    if not cs:
        try:
            import yaml
            cs = (yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}).get("case_study", "")
        except Exception:
            cs = ""
    case_dir = repo_root / "case_studies" / cs
    output_dir = Path(args.output_dir) if args.output_dir else case_dir / "output"
    return case_dir, output_dir


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Change-impact analysis over the trace JSONs.")
    parser.add_argument("command", nargs="?", default="report", choices=["snapshot", "report"])
    parser.add_argument("--case-study", default="")
    parser.add_argument("--config", default="")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args(argv)

    case_dir, output_dir = _resolve_paths(args)
    requirements = load_requirements(case_dir)
    links = load_links(output_dir)
    baseline_path = output_dir / "cia_baseline.json"

    if args.command == "snapshot":
        output_dir.mkdir(parents=True, exist_ok=True)
        snap = snapshot(requirements, links, created=datetime.now().isoformat(timespec="seconds"))
        baseline_path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        print(f"Baseline written to {baseline_path} "
              f"({len(requirements)} requirements, {len(links)} trace links).")
        return 0

    if not baseline_path.is_file():
        print("No baseline found. Run `python change_impact.py snapshot` first.", file=sys.stderr)
        return 2
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    report = impact(diff(baseline, requirements), build_graph(links), requirements)
    (output_dir / "cia_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(format_report(report))
    d = report["summary"]
    return 3 if (d["changed"] or d["added"] or d["removed"]) else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
