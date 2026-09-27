"""Convert model-creation Emfatic inputs to Ecore XML."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from ..emfatic.metrics import ClassDef, Feature, parse_emfatic_text
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from emfatic.metrics import ClassDef, Feature, parse_emfatic_text


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

_NAMESPACE_RE = re.compile(
    r"@namespace\s*\(\s*uri\s*=\s*[\"'](?P<uri>[^\"']+)[\"']\s*,\s*prefix\s*=\s*[\"'](?P<prefix>[^\"']+)[\"']\s*\)",
    re.I,
)
_PACKAGE_RE = re.compile(r"\bpackage\s+(?P<name>[A-Za-z_]\w*)\s*;", re.I)


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


def _add_structural_feature(parent: ET.Element, feature: Feature, classes: dict[str, ClassDef]) -> None:
    lower, upper = _bound_values(feature.upper)
    attrs = {"name": feature.name}
    if feature.kind == "attribute":
        attrs[f"{{{NS_XSI}}}type"] = "ecore:EAttribute"
        attrs["eType"] = _attribute_type(feature.type_name)
    else:
        attrs[f"{{{NS_XSI}}}type"] = "ecore:EReference"
        attrs["eType"] = (
            f"#//{feature.type_name}"
            if feature.type_name in classes
            else _attribute_type(feature.type_name)
        )
        if feature.containment:
            attrs["containment"] = "true"
    if lower is not None:
        attrs["lowerBound"] = lower
    if upper is not None:
        attrs["upperBound"] = upper
    ET.SubElement(parent, "eStructuralFeatures", attrs)


def emfatic_text_to_ecore_tree(text: str, fallback_name: str = "generated") -> ET.ElementTree:
    classes = parse_emfatic_text(text)
    if not classes:
        raise ValueError("no classes parsed from Emfatic text")

    package_name, ns_uri, ns_prefix = _package_metadata(text, fallback_name)
    root = ET.Element(
        f"{{{NS_ECORE}}}EPackage",
        {
            f"{{{NS_XMI}}}version": "2.0",
            "name": package_name,
            "nsURI": ns_uri,
            "nsPrefix": ns_prefix,
        },
    )
    for cls in classes.values():
        attrs = {
            f"{{{NS_XSI}}}type": "ecore:EClass",
            "name": cls.name,
        }
        if cls.abstract:
            attrs["abstract"] = "true"
        if cls.supertypes:
            attrs["eSuperTypes"] = " ".join(f"#//{name}" for name in cls.supertypes if name in classes)
        elem = ET.SubElement(root, "eClassifiers", attrs)
        for feature in cls.features:
            _add_structural_feature(elem, feature, classes)
    return ET.ElementTree(root)


def convert_file(input_path: Path, output_path: Path) -> None:
    ET.register_namespace("xmi", NS_XMI)
    ET.register_namespace("xsi", NS_XSI)
    ET.register_namespace("ecore", NS_ECORE)
    text = Path(input_path).read_text(encoding="utf-8")
    tree = emfatic_text_to_ecore_tree(text, fallback_name=Path(input_path).stem)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)
