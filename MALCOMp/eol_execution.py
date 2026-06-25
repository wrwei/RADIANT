"""Execution helpers for validating generated EOL against generated Emfatic DSLs."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


NS_XMI = "http://www.omg.org/XMI"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_ECORE = "http://www.eclipse.org/emf/2002/Ecore"
ECORE_DATATYPE_PREFIX = "ecore:EDataType http://www.eclipse.org/emf/2002/Ecore#//"
PRIMITIVE_DATATYPES = {
    "string": "EString",
    "str": "EString",
    "boolean": "EBoolean",
    "bool": "EBoolean",
    "real": "EFloat",
    "double": "EDouble",
    "float": "EFloat",
    "int": "EInt",
    "integer": "EInt",
    "nat": "EInt",
    "long": "ELong",
    "short": "EShort",
    "byte": "EByte",
    "char": "EChar",
}

_CLASS_RE = re.compile(
    r"""
    (?P<abstract>abstract\s+)?
    class\s+(?P<name>[A-Za-z_][\w]*)
    (?:\s+extends\s+(?P<super>[A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w]*)*))?
    \s*\{
    (?P<body>[^{}]*)
    \}
    """,
    re.VERBOSE | re.DOTALL,
)
_FEATURE_RE = re.compile(
    r"""
    (?P<kind>attr|val|ref)\s+
    (?P<type>[A-Za-z_][\w]*)
    (?:\[(?P<bound>[^\]]+)\])?
    \s+
    (?P<name>[A-Za-z_][\w]*)
    \s*;?
    """,
    re.VERBOSE,
)
_NAMESPACE_RE = re.compile(
    r"@namespace\s*\(\s*uri\s*=\s*[\"'](?P<uri>[^\"']+)[\"']\s*,\s*prefix\s*=\s*[\"'](?P<prefix>[^\"']+)[\"']\s*\)",
    re.I,
)
_PACKAGE_RE = re.compile(r"\bpackage\s+(?P<name>[A-Za-z_]\w*)\s*;", re.I)


@dataclass(frozen=True)
class EolExecutionResult:
    ok: bool
    exit_code: int
    model_path: Path
    stdout: str
    stderr: str
    error_summary: str
    # Conformance of the produced model to its metamodel (EMF Diagnostician).
    # None = check could not run (e.g. runner predates the --conformance mode).
    conformant: bool | None = None
    conformance_summary: str = ""


_CONFORMANCE_MARKER = "CONFORMANCE_JSON:"


@dataclass(frozen=True)
class ConformanceResult:
    conformant: bool | None  # None when the check could not run
    error_count: int
    warning_count: int
    summary: str  # human/LLM-readable list of violations


def check_conformance(
    runner: Path,
    model_path: Path,
    ecore_path: Path,
    timeout_seconds: int = 60,
) -> ConformanceResult:
    """Validate a produced model against its metamodel via MALCOMj's generic
    EMF Diagnostician (``--conformance``). Fail-soft: returns conformant=None if
    the runner doesn't emit the CONFORMANCE_JSON marker (older jar) or errors."""
    spec = f"{model_path};{ecore_path}"
    try:
        result = subprocess.run(
            [str(runner), "--conformance", spec],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as ex:  # noqa: BLE001 - runner missing / timeout -> unknown
        return ConformanceResult(None, 0, 0, f"conformance check could not run: {ex}")

    payload = None
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if line.startswith(_CONFORMANCE_MARKER):
            try:
                payload = json.loads(line[len(_CONFORMANCE_MARKER):].strip())
            except json.JSONDecodeError:
                payload = None
            break
    if payload is None:
        return ConformanceResult(None, 0, 0, "conformance check produced no verdict")

    violations = payload.get("violations", [])
    lines = [f"- [{v.get('severity', '?')}] {v.get('message', '')}" for v in violations]
    summary = "\n".join(lines) if lines else "model conforms to the metamodel"
    return ConformanceResult(
        conformant=bool(payload.get("conformant", False)),
        error_count=int(payload.get("errorCount", 0)),
        warning_count=int(payload.get("warningCount", 0)),
        summary=summary,
    )


def _bound_values(bound: str) -> tuple[str | None, str | None]:
    text = (bound or "1").strip()
    if text == "*":
        return None, "-1"
    if text == "?":
        return "0", None
    if ".." in text:
        lower, upper = [part.strip() for part in text.split("..", 1)]
        return lower or None, "-1" if upper == "*" else (upper or None)
    if text.isdigit():
        return text if text != "1" else None, text if text != "1" else None
    return None, None


def _package_metadata(text: str, fallback_name: str) -> tuple[str, str, str]:
    package_match = _PACKAGE_RE.search(text)
    name = package_match.group("name") if package_match else fallback_name
    namespace_match = _NAMESPACE_RE.search(text)
    if namespace_match:
        return name, namespace_match.group("uri"), namespace_match.group("prefix")
    return name, f"http://generated/{name}", name


def _attribute_type(type_name: str) -> str:
    ecore_name = PRIMITIVE_DATATYPES.get(type_name.casefold())
    return f"{ECORE_DATATYPE_PREFIX}{ecore_name}" if ecore_name else f"#//{type_name}"


def _parse_emfatic_classes(text: str) -> dict[str, dict[str, object]]:
    classes: dict[str, dict[str, object]] = {}
    for match in _CLASS_RE.finditer(text):
        name = match.group("name")
        super_text = match.group("super") or ""
        classes[name] = {
            "abstract": bool(match.group("abstract")),
            "supertypes": [s.strip() for s in super_text.split(",") if s.strip()],
            "features": [],
        }
        body = match.group("body") or ""
        for feat in _FEATURE_RE.finditer(body):
            classes[name]["features"].append({
                "kind": feat.group("kind"),
                "type": feat.group("type"),
                "bound": feat.group("bound") or "1",
                "name": feat.group("name"),
            })
    return classes


def convert_emfatic_to_ecore(input_path: Path, output_path: Path) -> None:
    text = Path(input_path).read_text(encoding="utf-8")
    classes = _parse_emfatic_classes(text)
    if not classes:
        raise ValueError(f"no classes parsed from {input_path}")

    ET.register_namespace("xmi", NS_XMI)
    ET.register_namespace("xsi", NS_XSI)
    ET.register_namespace("ecore", NS_ECORE)
    package_name, ns_uri, ns_prefix = _package_metadata(text, input_path.stem)
    root = ET.Element(
        f"{{{NS_ECORE}}}EPackage",
        {
            f"{{{NS_XMI}}}version": "2.0",
            "name": package_name,
            "nsURI": ns_uri,
            "nsPrefix": ns_prefix,
        },
    )
    for class_name, cls in classes.items():
        attrs = {
            f"{{{NS_XSI}}}type": "ecore:EClass",
            "name": class_name,
        }
        if cls["abstract"]:
            attrs["abstract"] = "true"
        supertypes = [f"#//{name}" for name in cls["supertypes"] if name in classes]
        if supertypes:
            attrs["eSuperTypes"] = " ".join(supertypes)
        elem = ET.SubElement(root, "eClassifiers", attrs)
        for feature in cls["features"]:
            _add_feature(elem, feature, classes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output_path, encoding="UTF-8", xml_declaration=True)


def _add_feature(parent: ET.Element, feature: dict[str, str], classes: dict[str, dict[str, object]]) -> None:
    lower, upper = _bound_values(feature["bound"])
    attrs = {"name": feature["name"]}
    if feature["kind"] == "attr":
        attrs[f"{{{NS_XSI}}}type"] = "ecore:EAttribute"
        attrs["eType"] = _attribute_type(feature["type"])
    else:
        attrs[f"{{{NS_XSI}}}type"] = "ecore:EReference"
        attrs["eType"] = (
            f"#//{feature['type']}"
            if feature["type"] in classes
            else _attribute_type(feature["type"])
        )
        if feature["kind"] == "val":
            attrs["containment"] = "true"
    if lower is not None:
        attrs["lowerBound"] = lower
    if upper is not None:
        attrs["upperBound"] = upper
    ET.SubElement(parent, "eStructuralFeatures", attrs)


def execute_eol(
    runner: Path,
    eol_path: Path,
    ecore_path: Path,
    attempt_model_path: Path,
    accepted_model_path: Path,
    timeout_seconds: int = 60,
) -> EolExecutionResult:
    attempt_model_path.parent.mkdir(parents=True, exist_ok=True)
    if attempt_model_path.exists():
        attempt_model_path.unlink()

    spec = f"M={attempt_model_path};{ecore_path};readOnLoad=false,storeOnDisposal=true"
    result = subprocess.run(
        [str(runner), "--script", str(eol_path), "--emf", spec],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    executed = result.returncode == 0 and attempt_model_path.is_file()

    # The EOL running without throwing only means a file was written — it does NOT
    # mean the model conforms to the metamodel. Validate the produced model with
    # EMF's Diagnostician and treat a non-conformant model as a failure so the
    # repair agent is given the concrete violations to fix.
    conformant: bool | None = None
    conformance_summary = ""
    if executed:
        conf = check_conformance(runner, attempt_model_path, ecore_path, timeout_seconds)
        conformant = conf.conformant
        conformance_summary = conf.summary

    # conformant is None => check could not run (older jar): fall back to the old
    # exit-code behaviour so the pipeline still works without the rebuilt runner.
    ok = executed and (conformant is not False)
    if ok:
        accepted_model_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(attempt_model_path, accepted_model_path)

    if not executed:
        error_summary = summarise_execution_error(result.stderr + "\n" + result.stdout)
    elif conformant is False:
        error_summary = "Model is non-conformant to the metamodel (EMF Diagnostician):\n" + conformance_summary
    else:
        error_summary = ""

    return EolExecutionResult(
        ok=ok,
        exit_code=result.returncode,
        model_path=accepted_model_path if ok else attempt_model_path,
        stdout=result.stdout,
        stderr=result.stderr,
        error_summary=error_summary,
        conformant=conformant,
        conformance_summary=conformance_summary,
    )


def summarise_execution_error(text: str, limit: int = 1200) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("Exception") or "Property '" in line or "Parse errors" in line:
            return line[:limit]
    return (lines[-1] if lines else "unknown EOL execution error")[:limit]
