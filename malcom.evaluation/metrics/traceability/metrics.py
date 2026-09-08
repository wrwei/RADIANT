"""Trace-link resolvability and requirement coverage.

Two metrics, defined as the paper defines them:

* **resolvability** — the fraction of emitted links whose target element
  actually exists in the generated artefact. A link is *resolved* when the
  pipeline's own locator finds its target; anything else is unresolved.
* **coverage** — the fraction of requirements with at least one link.

Resolution deliberately reuses ``MALCOMp.trace_locator``, the same machinery
the pipeline uses to stamp ``source.resolved`` during generation, so this
driver measures the property the pipeline claims rather than a re-implemented
approximation of it. Where a trace entry already carries a recorded
``source.resolved``, agreement with the recomputed verdict is reported too:
a disagreement means the artefact and its trace file have drifted apart.

Per layer, a link's target lives in a different artefact:

===========  ==========================  ===================================
layer        target artefact             locator kind / element field
===========  ==========================  ===================================
concept      the requirement text        ``requirement`` / Instance, Concept
notation     the Emfatic metamodel       ``emfatic``     / Emfatic_class
model        the EOL construction file   ``eol``         / Model_Element_id
behaviour    the RoboChart state machine ``robochart``   / transition
===========  ==========================  ===================================
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# The pipeline's locators are the reference implementation of "resolves".
_MALCOMP = Path(__file__).resolve().parents[3] / "MALCOMp"
if str(_MALCOMP) not in sys.path:
    sys.path.insert(0, str(_MALCOMP))

import trace_locator  # noqa: E402


# Per-layer spec. Filenames are candidates: run directories and the fixtures
# directory use different names for the same artefact.
LAYERS = (
    dict(layer="concept",
         trace=("result_term_extraction.json", "result_concept_trace.json"),
         tag="term_trace", legacy=("req",),
         artefact=(),                      # target is the requirement text
         kind="requirement",
         elements=("Instance", "Concept")),
    dict(layer="notation",
         trace=("result_dsl_extraction.json", "result_dsml_trace.json"),
         tag="dsl_trace", legacy=(),
         artefact=("result_DSL.emf", "result_dsml.emf"),
         kind="emfatic",
         elements=("Emfatic_class",)),
    dict(layer="model",
         trace=("result_model_creation.json", "result_model_trace.json"),
         tag="model_trace", legacy=(),
         artefact=("result_eol_program.eol", "result_model.eol"),
         kind="eol",
         elements=("Model_Element_id", "Model_Element")),
    dict(layer="behaviour",
         trace=("result_statemachine_extraction.json",
                "result_behaviour_trace.json"),
         tag="stm_trace", legacy=(),
         artefact=("STM.txt", "result_behaviour_complete.rct",
                   "result_behaviour_model.rct"),
         kind="robochart",
         elements=("transition",)),
)

ARCHITECTURAL_LAYERS = ("concept", "notation", "model")


def canonical_gid(value) -> str:
    """Requirement id, punctuation- and case-insensitive (as MALCOMp does)."""
    return re.sub(r"[^0-9a-z]", "", str(value or "").lower())


@dataclass
class LayerScore:
    layer: str
    links_emitted: int = 0          # entries carrying an element id
    links_resolved: int = 0
    links_without_element: int = 0  # entries with no target to resolve
    # The concept layer names either a specific INSTANCE the requirement
    # introduces ("AUV_Platform") or, when there is none, the metamodel TYPE
    # the requirement mentions ("RoboticPlatform"). These behave very
    # differently: an instance is quoted verbatim in the requirement text, a
    # type name is usually written as prose ("Robotic Platform"), so it does
    # not resolve by identifier matching. Reported separately — pooling them
    # mixes a link to a named element with a type annotation.
    instance_emitted: int = 0
    instance_resolved: int = 0
    typename_emitted: int = 0
    typename_resolved: int = 0
    requirements_total: int = 0
    requirements_covered: int = 0           # >= 1 emitted link (paper's def.)
    requirements_covered_resolved: int = 0  # >= 1 link that also resolves
    recorded_agree: int = 0         # entries whose source.resolved matches
    recorded_total: int = 0
    unresolved_examples: list = field(default_factory=list)
    artefact: str = ""
    trace_file: str = ""
    legacy_tag: str = ""

    @property
    def resolvability(self):
        if not self.links_emitted:
            return None
        return self.links_resolved / self.links_emitted

    @property
    def instance_resolvability(self):
        """Resolvability over links naming a specific element (excludes the
        concept layer's type-name fallback). Equals `resolvability` elsewhere."""
        if not self.instance_emitted:
            return None
        return self.instance_resolved / self.instance_emitted

    @property
    def typename_resolvability(self):
        if not self.typename_emitted:
            return None
        return self.typename_resolved / self.typename_emitted

    @property
    def coverage(self):
        """Fraction of in-scope requirements with at least one emitted link."""
        if not self.requirements_total:
            return None
        return self.requirements_covered / self.requirements_total

    @property
    def effective_coverage(self):
        """Coverage counting only requirements whose link actually resolves —
        the stricter reading, and the one that bounds change-impact recall."""
        if not self.requirements_total:
            return None
        return self.requirements_covered_resolved / self.requirements_total

    @property
    def recorded_agreement(self):
        if not self.recorded_total:
            return None
        return self.recorded_agree / self.recorded_total

    def as_row(self) -> dict:
        return {
            "layer": self.layer,
            "links_emitted": self.links_emitted,
            "links_resolved": self.links_resolved,
            "resolvability": self.resolvability,
            "instance_emitted": self.instance_emitted,
            "instance_resolvability": self.instance_resolvability,
            "typename_emitted": self.typename_emitted,
            "typename_resolvability": self.typename_resolvability,
            "links_without_element": self.links_without_element,
            "requirements_total": self.requirements_total,
            "requirements_covered": self.requirements_covered,
            "coverage": self.coverage,
            "effective_coverage": self.effective_coverage,
            "recorded_agreement": self.recorded_agreement,
            "artefact": self.artefact,
            "trace_file": self.trace_file,
            "legacy_tag": self.legacy_tag,
        }


def _first_existing(root: Path, names) -> Path | None:
    for n in names:
        p = root / n
        if p.is_file():
            return p
    return None


def _entries(data, tag: str, legacy) -> tuple[list, str]:
    """Entries under `tag`, else under a legacy tag (returned for reporting)."""
    if not isinstance(data, dict):
        return [], ""
    if isinstance(data.get(tag), list):
        return data[tag], ""
    for old in legacy:
        if isinstance(data.get(old), list):
            return data[old], old
    return [], ""


def load_requirements(case_dir) -> dict:
    """{canonical gid: (description, kind)} over a case study's requirements.

    `kind` is 'behaviour' for the behavioural requirement file and
    'architecture' otherwise, so coverage can be scoped to the layers that are
    supposed to link a given requirement.
    """
    out: dict[str, tuple[str, str]] = {}
    req_dir = Path(case_dir) / "requirements"
    for path in sorted(req_dir.glob("requirement_*.json")):
        kind = "behaviour" if "behaviour" in path.stem else "architecture"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items = data.get("requirements") if isinstance(data, dict) else data
        for r in items or []:
            if not isinstance(r, dict):
                continue
            gid = canonical_gid(r.get("id") or r.get("gid") or r.get("GID"))
            if gid and gid not in out:
                out[gid] = (r.get("description", ""), kind)
    return out


def score_run(run_dir, requirements: dict) -> list[LayerScore]:
    """Resolvability and coverage for each layer of one run directory."""
    run_dir = Path(run_dir)
    scores = []
    for spec in LAYERS:
        s = LayerScore(layer=spec["layer"])
        trace_path = _first_existing(run_dir, spec["trace"])
        if trace_path is None:
            scores.append(s)
            continue
        s.trace_file = trace_path.name
        try:
            data = json.loads(trace_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            scores.append(s)
            continue
        entries, legacy = _entries(data, spec["tag"], spec["legacy"])
        s.legacy_tag = legacy

        artefact_text = ""
        if spec["artefact"]:
            artefact = _first_existing(run_dir, spec["artefact"])
            if artefact is None:
                scores.append(s)     # no artefact => nothing can resolve
                continue
            s.artefact = artefact.name
            artefact_text = artefact.read_text(encoding="utf-8", errors="replace")
        else:
            s.artefact = "requirement text"

        covered = set()
        covered_resolved = set()
        for e in entries:
            if not isinstance(e, dict):
                continue
            gid = canonical_gid(e.get("requirement_gid") or e.get("GID")
                                or e.get("gid"))
            field_used = next((f for f in spec["elements"]
                               if e.get(f) not in (None, "", [])), None)
            if field_used is None:
                s.links_without_element += 1
                continue
            element = e[field_used]
            # Only the concept layer has a type-name fallback; for every other
            # layer the first (and only) field names a specific element.
            is_typename = (spec["kind"] == "requirement"
                           and field_used == "Concept")
            s.links_emitted += 1

            # The concept layer resolves against the requirement's own text.
            text = artefact_text
            if spec["kind"] == "requirement":
                text = requirements.get(gid, ("", ""))[0]

            resolved = bool(text) and trace_locator.locate(
                spec["kind"], str(element), text) is not None
            if is_typename:
                s.typename_emitted += 1
                s.typename_resolved += int(resolved)
            else:
                s.instance_emitted += 1
                s.instance_resolved += int(resolved)
            # Coverage is "requirements with at least one link" (the paper's
            # definition), so it counts EMITTED links; resolvability is the
            # separate question of whether those links land. Requiring
            # resolution here would conflate the two metrics.
            if gid:
                covered.add(gid)
                if resolved:
                    covered_resolved.add(gid)
            if resolved:
                s.links_resolved += 1
            elif len(s.unresolved_examples) < 8:
                tag = " (type name)" if is_typename else ""
                s.unresolved_examples.append(f"{gid or '?'}:{element}{tag}")

            recorded = (e.get("source") or {}).get("resolved")
            if isinstance(recorded, bool):
                s.recorded_total += 1
                s.recorded_agree += int(recorded == resolved)

        scope = "behaviour" if spec["layer"] == "behaviour" else "architecture"
        in_scope = {g for g, (_, k) in requirements.items() if k == scope}
        s.requirements_total = len(in_scope)
        s.requirements_covered = len(covered & in_scope)
        s.requirements_covered_resolved = len(covered_resolved & in_scope)
        scores.append(s)
    return scores


def aggregate(run_scores) -> list[dict]:
    """Pool layer scores across runs (link-weighted, i.e. micro-averaged)."""
    out = []
    for idx, spec in enumerate(LAYERS):
        emitted = sum(r[idx].links_emitted for r in run_scores)
        resolved = sum(r[idx].links_resolved for r in run_scores)
        i_em = sum(r[idx].instance_emitted for r in run_scores)
        i_res = sum(r[idx].instance_resolved for r in run_scores)
        t_em = sum(r[idx].typename_emitted for r in run_scores)
        t_res = sum(r[idx].typename_resolved for r in run_scores)
        # Average coverage only over runs whose layer actually produced links.
        # A run that emitted none (a failed phase — e.g. a trace file of empty
        # objects) would otherwise enter as a 0.0 and be indistinguishable from
        # genuinely poor coverage. Such runs are counted in `runs_empty`.
        scored = [r[idx] for r in run_scores if r[idx].links_emitted]
        cov = [x.coverage for x in scored if x.coverage is not None]
        eff = [x.effective_coverage for x in scored
               if x.effective_coverage is not None]
        agree = sum(r[idx].recorded_agree for r in run_scores)
        rec = sum(r[idx].recorded_total for r in run_scores)
        out.append({
            "layer": spec["layer"],
            "runs": len(scored),
            "runs_empty": sum(1 for r in run_scores
                              if r[idx].trace_file and not r[idx].links_emitted),
            "links_emitted": emitted,
            "links_resolved": resolved,
            "resolvability": (resolved / emitted) if emitted else None,
            "instance_emitted": i_em,
            "instance_resolvability": (i_res / i_em) if i_em else None,
            "typename_emitted": t_em,
            "typename_resolvability": (t_res / t_em) if t_em else None,
            "coverage_mean": (sum(cov) / len(cov)) if cov else None,
            "coverage_min": min(cov) if cov else None,
            "coverage_max": max(cov) if cov else None,
            "effective_coverage_mean": (sum(eff) / len(eff)) if eff else None,
            "recorded_agreement": (agree / rec) if rec else None,
        })
    arch = [r for r in out if r["layer"] in ARCHITECTURAL_LAYERS]
    emitted = sum(r["links_emitted"] for r in arch)
    resolved = sum(r["links_resolved"] for r in arch)
    i_em = sum(r["instance_emitted"] for r in arch)
    i_res = sum(int(round((r["instance_resolvability"] or 0) * r["instance_emitted"]))
                for r in arch)
    covs = [r["coverage_mean"] for r in arch if r["coverage_mean"] is not None]
    out.append({
        "layer": "architectural (pooled)",
        "runs": max((r["runs"] for r in arch), default=0),
        "runs_empty": max((r["runs_empty"] for r in arch), default=0),
        "links_emitted": emitted,
        "links_resolved": resolved,
        "resolvability": (resolved / emitted) if emitted else None,
        "instance_emitted": i_em,
        "instance_resolvability": (i_res / i_em) if i_em else None,
        "typename_emitted": sum(r["typename_emitted"] for r in arch),
        "typename_resolvability": None,
        "coverage_mean": (sum(covs) / len(covs)) if covs else None,
        "coverage_min": min(covs) if covs else None,
        "coverage_max": max(covs) if covs else None,
        "effective_coverage_mean": None,
        "recorded_agreement": None,
    })
    return out
