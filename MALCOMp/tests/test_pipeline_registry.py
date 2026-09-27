"""Golden test: the LAYERS registry must match the live stage classes.

Constructing a stage builds its ConversableAgents but makes NO API call, so
this runs offline with a dummy key. If a create_agent() call drifts from the
registry roster, this fails immediately. Side agents created directly (e.g.
the emf layer's EOL_Repairer) are not appended to self.agents and so are
correctly excluded from the roster comparison.
"""
import sys
from pathlib import Path

import pytest
import yaml

MALCOMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MALCOMP))

from pipeline import LAYERS  # noqa: E402

CONFIG = MALCOMP.parent / "config.yaml"


@pytest.fixture(autouse=True)
def _dummy_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")


@pytest.mark.parametrize("key", list(LAYERS))
def test_registry_roster_matches_live_agents(key):
    spec = LAYERS[key]
    stage = spec.cls(config_path=str(CONFIG))
    assert tuple(a.name for a in stage.agents) == spec.agent_names


@pytest.mark.parametrize("key", list(LAYERS))
def test_config_key_exists(key):
    spec = LAYERS[key]
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert spec.config_key in config["stages"]


@pytest.mark.parametrize("key", list(LAYERS))
def test_each_layer_has_one_primary(key):
    spec = LAYERS[key]
    assert sum(1 for a in spec.agents if a.primary) == 1


def test_missing_case_study_fails_fast(monkeypatch, tmp_path):
    """A missing/typo'd case study must raise an actionable FileNotFoundError
    up front — naming the study and the case_studies/ layout — rather than a
    cryptic feeder error, and must NOT silently create the bogus case dir."""
    monkeypatch.setenv("MALCOMP_CASE_STUDY", "definitely_not_a_real_case_study")
    spec = next(iter(LAYERS.values()))
    with pytest.raises(FileNotFoundError) as exc:
        spec.cls(config_path=str(CONFIG))
    msg = str(exc.value)
    assert "definitely_not_a_real_case_study" in msg
    assert "case_studies" in msg
    # The bogus study directory must not have been materialised by output/'s mkdir.
    assert not (CONFIG.parent / "case_studies" / "definitely_not_a_real_case_study").exists()


def test_enrich_reads_fresh_artefact_on_rerun(tmp_path):
    """A reused stage instance (the web 'refine' flow re-runs a cached stage)
    must enrich against the freshly-written artefact, not a stale memoised copy."""
    from phases.dsml import DSMLCreation
    stage = DSMLCreation(config_path=str(CONFIG))
    stage.output_dir = tmp_path
    code_file = stage.stage_config["output"]["code_file"]
    (tmp_path / code_file).write_text("class Sensor {\n}\n", encoding="utf-8")
    e1 = [{"requirement_gid": "X1", "Emfatic_class": "Sensor"}]
    stage._enrich_trace_entries(e1)
    assert e1[0]["source"]["line_start"] == 1
    # Refine re-run: same instance, artefact rewritten with Sensor lower down.
    (tmp_path / code_file).write_text("// h\n// h\nclass Sensor {\n}\n", encoding="utf-8")
    e2 = [{"requirement_gid": "X1", "Emfatic_class": "Sensor"}]
    stage._enrich_trace_entries(e2)
    assert e2[0]["source"]["line_start"] == 3  # fresh read, not the stale cache


def test_behaviour_run_streams_each_agent(tmp_path, monkeypatch):
    """Phase 5's custom run() must emit each agent's message to the active
    IOStream so the web UI shows live agent activity (as phases 2-4 do)."""
    from phases.behaviour import BehaviourModelCreation
    from autogen.io import IOStream
    stage = BehaviourModelCreation(config_path=str(CONFIG))
    stage.output_dir = tmp_path  # avoid polluting the real auv output/
    dsl = "stm S { state Move { } transition t0 { from i0 to Move } }"
    monkeypatch.setattr(stage.modeller, "generate_reply", lambda messages=None: dsl)
    monkeypatch.setattr(stage.checker, "generate_reply", lambda messages=None: dsl)
    monkeypatch.setattr(stage.json_generator, "generate_reply",
                        lambda messages=None: '[{"requirement_gid":"R1","transition":"t0"}]')

    captured = []

    class FakeStream:
        def send_agent_message(self, sender, content):
            captured.append(sender)
        def print(self, *a, **k):
            pass
        def input(self, *a, **k):
            return ""

    with IOStream.set_default(FakeStream()):
        stage.run()

    assert "Behaviour_Model_Creation_Agent" in captured
    assert "Behaviour_Checker_Agent" in captured
    assert "Trace_Generation_Agent" in captured


def test_announce_trace_flags_real_vs_echoed(monkeypatch):
    """A real trace (entries keyed to a requirement) is confirmed; requirements
    echoed back by a confused agent (no requirement id) are flagged."""
    from autogen.io import IOStream
    spec = next(iter(LAYERS.values()))
    stage = spec.cls(config_path=str(CONFIG))
    captured = []

    class S:
        def send_agent_message(self, sender, content):
            captured.append(content)

    with IOStream.set_default(S()):
        stage._announce_trace("result_dsml_trace.json",
                              [{"requirement_gid": "SD1", "Emfatic_class": "Module"}])
        stage._announce_trace("result_dsml_trace.json",
                              [{"kind": "NFR", "id": "SD1", "description": "x"}])
    assert "Traceability generated" in captured[0]
    assert captured[0].startswith("✓")
    assert captured[1].startswith("⚠")  # echoed requirements => flagged invalid


def test_concept_model_derived_from_trace(tmp_path):
    """Phase 2 writes a deduplicated concept model alongside the trace."""
    import json as _j
    from types import SimpleNamespace
    from phases.concept import ConceptExtraction
    stage = ConceptExtraction(config_path=str(CONFIG))
    stage.output_dir = tmp_path
    stage.user.data = [{"gid": "R1", "description": 'a Module named "M1"'}]
    content = ('[{"GID":"R1","Concept":"Module","Concept_description":"d",'
               '"Instance":"M1","Instance_of":"Module","Instance_description":""},'
               '{"GID":"R1","Concept":"Module","Instance":"M2","Instance_of":"Module"}]')
    result = SimpleNamespace(chat_history=[
        {"name": stage.user.name, "content": _j.dumps(stage.user.data[0])},
        {"name": "Trace_Generation_Agent", "content": content},
    ])
    stage.store_json(result, "Trace_Generation_Agent",
                     str(tmp_path / "result_concept_trace.json"), "term_trace")
    model_file = tmp_path / stage.stage_config["output"]["code_file"]
    assert model_file.exists(), "concept model file should be written"
    model = _j.loads(model_file.read_text(encoding="utf-8"))
    # "Module" deduplicated to one concept; two distinct instances M1, M2.
    assert [c["Concept"] for c in model["concepts"]] == ["Module"]
    assert sorted(i["Instance"] for i in model["instances"]) == ["M1", "M2"]


def test_feeds_sequential_vs_batch():
    import json as _j
    from phases.concept import ConceptExtraction
    stage = ConceptExtraction(config_path=str(CONFIG))
    stage.user.data = [{"gid": "A"}, {"gid": "B"}]
    stage.feed_mode = "sequential"
    assert len(stage._feeds()) == 2
    stage.feed_mode = "batch"
    feeds = stage._feeds()
    assert len(feeds) == 1
    assert len(_j.loads(feeds[0])) == 2  # whole list in one payload


def test_round_robin_emits_progress(monkeypatch):
    from phases.concept import ConceptExtraction
    from autogen.io import IOStream
    stage = ConceptExtraction(config_path=str(CONFIG))
    stage.feed_mode = "sequential"  # this test exercises the per-requirement path
    stage.user.data = [{"gid": "A", "description": "x"}, {"gid": "B", "description": "y"}]
    for a in stage.agents:
        monkeypatch.setattr(a, "generate_reply", lambda messages=None: "{}")
    progress = []

    class S:
        def send_progress(self, c, t, agent):
            progress.append((c, t, agent))
        def send_agent_message(self, *a, **k):
            pass
        def print(self, *a, **k):
            pass
        def input(self, *a, **k):
            return ""

    with IOStream.set_default(S()):
        stage._run_round_robin()
    assert len(progress) == 6  # 2 requirements x 3 agents
    assert all(t == 2 for _, t, _ in progress)
    assert {c for c, _, _ in progress} == {1, 2}


def test_concept_batch_store_json_attributes_by_entry_gid(tmp_path):
    import json as _j
    from types import SimpleNamespace
    from phases.concept import ConceptExtraction
    stage = ConceptExtraction(config_path=str(CONFIG))
    stage.output_dir = tmp_path
    stage.feed_mode = "batch"
    stage.user.data = [{"gid": "A1"}, {"gid": "B2"}]
    content = ('[{"GID":"A1","Concept":"Sensor","Instance":"s"},'
               '{"GID":"B2","Concept":"Module","Instance":"m"}]')
    result = SimpleNamespace(
        chat_history=[{"name": "Trace_Generation_Agent", "content": content}])
    out = tmp_path / "out.json"
    stage.store_json(result, "Trace_Generation_Agent", str(out), "term_trace")
    data = _j.loads(out.read_text(encoding="utf-8"))
    assert [e["GID"] for e in data["term_trace"]] == ["A1", "B2"]


@pytest.mark.parametrize("key", list(LAYERS))
def test_phase_has_repair_agent_not_in_roster(key):
    """Every phase exposes a dedicated repair agent + target; the agent is a side
    agent (not in the LAYERS roster), like EOL_Repairer."""
    stage = LAYERS[key].cls(config_path=str(CONFIG))
    assert stage._repair_agent is not None
    assert stage._repair_target
    assert stage._repair_agent.name not in [a.name for a in stage.agents]


def test_verify_and_repair_loop(tmp_path, monkeypatch):
    """On verification failure, the repair agent is invoked and the artefact is
    re-verified; the loop converges when verification passes."""
    import json as _j
    import verification
    from phases.concept import ConceptExtraction
    stage = ConceptExtraction(config_path=str(CONFIG))
    stage.output_dir = tmp_path
    stage._repair_target = "art.json"
    (tmp_path / "art.json").write_text('{"bad": true}', encoding="utf-8")
    calls = {"n": 0}

    class RepairAgent:
        name = "Concept_Repair_Agent"
        def generate_reply(self, messages=None):
            calls["n"] += 1
            return '{"fixed": true}'

    stage._repair_agent = RepairAgent()
    seq = iter([
        verification.VerificationResult("concept", [
            verification.Check("schema", "structural", False, False, "bad")]),
        verification.VerificationResult("concept", [
            verification.Check("schema", "structural", True, False, "ok")]),
    ])
    monkeypatch.setattr(verification, "verify", lambda *a, **k: next(seq))
    stage._verify_and_repair()
    assert calls["n"] == 1                       # repair invoked once
    assert stage.verification_result.passed
    assert _j.loads((tmp_path / "art.json").read_text(encoding="utf-8"))["fixed"] is True


def test_gate_blocks_next_phase_on_failure():
    """gate_ok returns False (halt) when a result has hard failures."""
    import run as runner
    import verification
    failing = verification.VerificationResult("dsml", [
        verification.Check("emfatic_parses", "structural", False, False, "syntax error")])
    passing = verification.VerificationResult("dsml", [
        verification.Check("emfatic_parses", "structural", True, False, "ok")])
    assert runner.gate_ok(passing) is True
    assert runner.gate_ok(failing) is False
    assert runner.gate_ok(None) is True  # not gated when no result


def test_base_runs_verification(tmp_path, monkeypatch):
    """After a phase's run path, Base records a VerificationResult."""
    from phases.concept import ConceptExtraction
    stage = ConceptExtraction(config_path=str(CONFIG))
    stage.output_dir = tmp_path
    (tmp_path / "result_concept_trace.json").write_text(
        '{"term_trace":[{"GID":"X","Concept":"C","source":{"resolved":true}}]}', encoding="utf-8")
    (tmp_path / "result_concept_model.json").write_text('{"concepts":[],"instances":[]}', encoding="utf-8")
    stage._run_verification()
    assert stage.verification_result is not None
    assert stage.verification_result.passed


def test_behaviour_layer_has_checker():
    """Phase 5 should mirror the other LLM phases by including a checker that
    sits between the primary creator and the trace agent."""
    spec = LAYERS["behaviour"]
    assert spec.agent_names == (
        "Behaviour_Model_Creation_Agent",
        "Behaviour_Checker_Agent",
        "Trace_Generation_Agent",
    )


def test_concept_trace_source_char_span():
    from phases.concept import ConceptExtraction
    stage = ConceptExtraction(config_path=str(CONFIG))
    stage.user.data = [{"gid": "X1",
                        "description": 'The system uses a Sensor named "S1".'}]
    entry = {"GID": "X1", "Concept": "Sensor", "Instance": "S1"}
    source = stage._trace_source_for_entry(entry)
    assert source["file"] == "requirement:X1"
    assert source["resolved"] is True
    desc = stage.user.data[0]["description"]
    assert desc[source["char_start"]:source["char_end"]] == "S1"


def test_concept_trace_source_unresolved_when_absent():
    from phases.concept import ConceptExtraction
    stage = ConceptExtraction(config_path=str(CONFIG))
    stage.user.data = [{"gid": "X1", "description": "no instance text here"}]
    entry = {"GID": "X1", "Concept": "Sensor", "Instance": "Zzz"}
    source = stage._trace_source_for_entry(entry)
    assert source == {"file": "requirement:X1", "resolved": False}


def test_dsml_trace_source_line_span(tmp_path):
    from phases.dsml import DSMLCreation
    stage = DSMLCreation(config_path=str(CONFIG))
    stage.output_dir = tmp_path  # avoid polluting the real auv output/
    code_file = stage.stage_config["output"]["code_file"]
    (tmp_path / code_file).write_text(
        "abstract class NamedElement {\n    attr String name;\n}\n"
        "class Sensor extends NamedElement {\n}\n",
        encoding="utf-8",
    )
    stage._code_artefact_cache = None  # force re-read of what we just wrote
    entry = {"requirement_gid": "X1", "Emfatic_class": "Sensor"}
    source = stage._trace_source_for_entry(entry)
    assert source["file"] == "result_dsml.emf"
    assert source["resolved"] is True
    assert source["line_start"] == 4 and source["line_end"] == 5


def test_model_trace_source_line(tmp_path):
    from phases.model import EMFModelCreation
    stage = EMFModelCreation(config_path=str(CONFIG))
    stage.output_dir = tmp_path  # avoid polluting the real auv output/
    code_file = stage.stage_config["output"]["code_file"]
    (tmp_path / code_file).write_text(
        "{\nvar a_module = new M!Module;\na_module.name = \"A_Module\";\n}\n",
        encoding="utf-8",
    )
    stage._code_artefact_cache = None
    entry = {"requirement_gid": "X1", "Model_Element": "Module",
             "Model_Element_id": "A_Module"}
    source = stage._trace_source_for_entry(entry)
    assert source["file"] == "result_model.eol"
    assert source["resolved"] is True
    assert source["line_start"] == 3  # the .name = "A_Module" line


def test_behaviour_trace_source_block(tmp_path):
    from phases.behaviour import BehaviourModelCreation
    stage = BehaviourModelCreation(config_path=str(CONFIG))
    stage.output_dir = tmp_path  # avoid polluting the real auv output/
    code_file = stage.stage_config["output"]["code_file"]
    (tmp_path / code_file).write_text(
        "stm S {\n  state Move { }\n  transition t0 {\n"
        "    from i0\n    to Move\n  }\n}\n",
        encoding="utf-8",
    )
    stage._code_artefact_cache = None
    entry = {"requirement_gid": "X1", "source_state": "i0",
             "end_state": "Move", "transition": "t0"}
    source = stage._trace_source_for_entry(entry)
    assert source["resolved"] is True
    assert source["line_start"] == 3 and source["line_end"] == 6


def test_enrich_trace_entries_is_noop_by_default(monkeypatch):
    """Base._enrich_trace_entries must not alter entries when a stage defines
    no _trace_source_for_entry override beyond the default None."""
    spec = next(iter(LAYERS.values()))
    stage = spec.cls(config_path=str(CONFIG))
    # Force the default no-op hook regardless of subclass override.
    monkeypatch.setattr(type(stage), "_trace_source_for_entry",
                        lambda self, entry: None, raising=False)
    entries = [{"GID": "X1", "Concept": "Sensor"}]
    out = stage._enrich_trace_entries(entries)
    assert out == [{"GID": "X1", "Concept": "Sensor"}]
    assert "source" not in out[0]


def test_build_source_resolved_and_unresolved():
    spec = next(iter(LAYERS.values()))
    stage = spec.cls(config_path=str(CONFIG))
    assert stage._build_source("f.eol", (3, 5)) == {
        "file": "f.eol", "line_start": 3, "line_end": 5, "resolved": True}
    assert stage._build_source("requirement:X1", (2, 4), char=True) == {
        "file": "requirement:X1", "char_start": 2, "char_end": 4, "resolved": True}
    assert stage._build_source("f.eol", None) == {"file": "f.eol", "resolved": False}


@pytest.mark.parametrize("key", list(LAYERS))
def test_config_output_agents_exist_in_roster(key):
    """config.yaml output.json_agent / code_agent must name a real agent in
    the Layer's roster (or a known side agent) — otherwise Base.run silently
    writes an empty artefact. Renaming agents without updating these refs is
    the failure this guards."""
    spec = LAYERS[key]
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    output = config["stages"][spec.config_key].get("output", {})
    roster = set(spec.agent_names) | {"EOL_Repairer"}  # EOL_Repairer is a valid code source
    for ref_key in ("json_agent", "code_agent"):
        agent = output.get(ref_key)
        if agent is not None:
            assert agent in roster, (
                f"{spec.config_key}.output.{ref_key}={agent!r} not in roster {sorted(roster)}"
            )
