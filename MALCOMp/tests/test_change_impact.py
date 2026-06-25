"""Unit tests for the change-impact analysis facility."""
import json
import sys
from pathlib import Path

MALCOMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MALCOMP))


def _write(p: Path, obj):
    p.write_text(json.dumps(obj), encoding="utf-8")


def _src(line=1, resolved=True, file="f.rct"):
    return {"file": file, "line_start": line, "line_end": line, "resolved": resolved}


def _make_traces(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "result_concept_trace.json", {"term_trace": [
        {"GID": "SD1", "Concept": "Module", "Instance": "AUV_Module", "source": _src(1, file="c.json")}]})
    _write(out / "result_dsml_trace.json", {"dsl_trace": [
        {"requirement_gid": "SD1", "Emfatic_class": "Module", "source": _src(7, file="result_dsml.emf")}]})
    _write(out / "result_model_trace.json", {"model_trace": [
        {"requirement_gid": "SD1", "Model_Element": "Module", "Model_Element_id": "AUV_Module",
         "source": _src(2, file="result_model.eol")}]})
    _write(out / "result_behaviour_trace.json", {"stm_trace": [
        {"requirement_gid": "LRE1", "transition": "t0", "source_state": "i0", "end_state": "OCM",
         "source": _src(35, file="result_behaviour_model.rct")}]})


# --- load_links -------------------------------------------------------------

def test_load_links_normalises_each_phase(tmp_path):
    from change_impact import load_links
    _make_traces(tmp_path)
    links = load_links(tmp_path)
    by_phase = {l.phase: l for l in links}
    assert set(by_phase) == {"concept", "dsml", "model", "behaviour"}
    assert by_phase["concept"].gid == "sd1"                      # canonicalised
    assert by_phase["concept"].element == "Module: AUV_Module"
    assert by_phase["dsml"].element == "Module"
    assert by_phase["model"].element == "Module: AUV_Module"
    assert by_phase["behaviour"].element == "t0 (i0 -> OCM)"
    assert by_phase["dsml"].source["line_start"] == 7


def test_load_links_skips_missing_and_bad_files(tmp_path):
    from change_impact import load_links
    tmp_path.mkdir(parents=True, exist_ok=True)
    _write(tmp_path / "result_dsml_trace.json", {"dsl_trace": [
        {"requirement_gid": "SD1", "Emfatic_class": "Module", "source": _src(7)}]})
    (tmp_path / "result_model_trace.json").write_text("{not json", encoding="utf-8")
    links = load_links(tmp_path)
    assert [l.phase for l in links] == ["dsml"]                  # missing + bad skipped


# --- load_requirements ------------------------------------------------------

def test_load_requirements_merges_and_canonicalises(tmp_path):
    from change_impact import load_requirements
    reqs = tmp_path / "requirements"
    reqs.mkdir(parents=True)
    _write(reqs / "requirement_architecture.json", [{"gid": "SD-1", "description": "arch req"}])
    _write(reqs / "requirement_behaviour.json", [{"GID": "LRE1", "description": "beh req"}])
    out = load_requirements(tmp_path)
    assert out == {"sd1": "arch req", "lre1": "beh req"}


# --- diff -------------------------------------------------------------------

def test_diff_detects_changed_added_removed():
    from change_impact import diff
    baseline = {"requirements": {"sd1": "h1", "sd2": "h2", "sd3": "h3"}}
    # current: sd1 unchanged-hash supplied as text; helper hashes internally
    import change_impact as ci
    current = {"sd1": "same", "sd2": "MODIFIED", "sd4": "new"}
    # rebuild baseline hashes from a known prior text mapping
    baseline = {"requirements": {
        "sd1": ci._hash("same"), "sd2": ci._hash("old"), "sd3": ci._hash("gone")}}
    d = diff(baseline, current)
    assert d["changed"] == ["sd2"]
    assert d["added"] == ["sd4"]
    assert d["removed"] == ["sd3"]


# --- impact -----------------------------------------------------------------

def test_impact_fans_out_changed_flags_added_and_removed():
    from change_impact import impact, build_graph, Link
    links = [
        Link("sd1", "dsml", "Module", _src(7)),
        Link("sd1", "model", "Module: AUV_Module", _src(2)),
        Link("sd3", "behaviour", "t0 (i0 -> OCM)", _src(35)),   # removed req's orphan
    ]
    graph = build_graph(links)
    d = {"changed": ["sd1"], "added": ["sd4"], "removed": ["sd3"]}
    reqs = {"sd1": "req one", "sd4": "req four"}
    report = impact(d, graph, reqs)
    assert report["summary"]["changed"] == 1
    assert report["summary"]["affected_elements"] == 2          # sd1's two links
    ch = report["changed_requirements"][0]
    assert ch["gid"] == "sd1" and {a["phase"] for a in ch["affected"]} == {"dsml", "model"}
    assert report["added_requirements"][0]["gid"] == "sd4"
    assert report["removed_requirements"][0]["orphaned_elements"][0]["phase"] == "behaviour"


# --- snapshot + format ------------------------------------------------------

def test_snapshot_shape():
    from change_impact import snapshot, Link
    snap = snapshot({"sd1": "text"}, [Link("sd1", "dsml", "Module", _src(7))], created="2026-06-16")
    assert snap["created"] == "2026-06-16"
    assert "sd1" in snap["requirements"]
    assert snap["links"][0]["phase"] == "dsml"


def test_format_report_mentions_counts_and_elements():
    from change_impact import format_report
    report = {"summary": {"changed": 1, "added": 0, "removed": 0, "affected_elements": 1},
              "changed_requirements": [{"gid": "sd1", "text": "t", "affected": [
                  {"phase": "dsml", "element": "Module", "file": "result_dsml.emf",
                   "line_start": 7, "line_end": 14, "resolved": True}]}],
              "added_requirements": [], "removed_requirements": []}
    text = format_report(report)
    assert "sd1" in text and "Module" in text and "result_dsml.emf" in text


# --- build_thread -----------------------------------------------------------

def _make_reqs(case_dir):
    reqs = case_dir / "requirements"
    reqs.mkdir(parents=True, exist_ok=True)
    _write(reqs / "requirement_architecture.json",
           {"requirements": [{"id": "SD1", "name": "SysDesc1", "description": "d"}]})
    _write(reqs / "requirement_behaviour.json",
           {"requirements": [{"id": "LRE1", "name": "Lre1", "description": "b"}]})


def test_build_thread_shape(tmp_path):
    from change_impact import build_thread
    out = tmp_path / "output"
    _make_traces(out)
    _make_reqs(tmp_path)
    g = build_thread(out, tmp_path)
    assert g["columns"] == ["requirement", "concept", "dsml", "model", "behaviour"]
    rids = {n["id"]: n for n in g["nodes"]["requirement"]}
    assert set(rids) == {"SD1", "LRE1"}
    assert rids["SD1"]["traced"] and rids["LRE1"]["traced"]
    assert rids["SD1"]["cid"] == "sd1"
    assert all(len(g["nodes"][p]) == 1 for p in ("concept", "dsml", "model", "behaviour"))
    assert len(g["links"]) == 4
    assert {l["from"] for l in g["links"]} == {"sd1", "lre1"}
    assert g["stats"]["total_links"] == 4
    assert g["stats"]["by_phase"]["concept"] == 1


def test_build_thread_untraced_requirement_is_greyed(tmp_path):
    from change_impact import build_thread
    out = tmp_path / "output"
    _make_traces(out)
    reqs = tmp_path / "requirements"
    reqs.mkdir(parents=True, exist_ok=True)
    _write(reqs / "requirement_architecture.json",
           {"requirements": [{"id": "SD1", "name": "x", "description": "d"},
                             {"id": "SD9", "name": "untraced", "description": "u"}]})
    g = build_thread(out, tmp_path)
    sd9 = next(n for n in g["nodes"]["requirement"] if n["id"] == "SD9")
    assert sd9["traced"] is False


def test_build_thread_marks_cia_impact(tmp_path):
    from change_impact import build_thread
    out = tmp_path / "output"
    _make_traces(out)
    _make_reqs(tmp_path)
    _write(out / "cia_report.json", {
        "summary": {"changed": 1, "added": 0, "removed": 0, "affected_elements": 1},
        "changed_requirements": [{"gid": "sd1", "text": "d",
            "affected": [{"phase": "concept", "element": "Module: AUV_Module"}]}],
        "added_requirements": [], "removed_requirements": [],
    })
    g = build_thread(out, tmp_path)
    sd1 = next(n for n in g["nodes"]["requirement"] if n["id"] == "SD1")
    assert sd1["impacted"] is True
    assert g["nodes"]["concept"][0]["impacted"] is True
    assert any(l["impacted"] for l in g["links"] if l["phase"] == "concept")
