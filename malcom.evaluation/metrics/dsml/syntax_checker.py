"""Run the official Eclipse Emfatic parser for syntax validation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


HELPER_CLASS = "org.sawg.malcomj.EmfaticHelper"


@dataclass(frozen=True)
class SyntaxCheck:
    syntax_ok: bool
    errors: tuple[dict[str, object], ...]
    warnings: tuple[dict[str, object], ...]
    builder_errors: tuple[str, ...] = ()

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def error_summary(self) -> str:
        return "; ".join(str(item.get("message", "")) for item in self.errors)


def _jar_files(root: Path) -> list[Path]:
    try:
        return sorted(path for path in root.rglob("*.jar") if path.is_file())
    except OSError:
        return []


def discover_classpath(repo_root: Path, gradle_user_home: Path | None = None) -> str:
    """Locate EmfaticHelper plus its runtime dependencies.

    A Gradle application installation is preferred. The Gradle cache fallback
    supports development checkouts where only compiled classes are available.
    """
    malcomj = repo_root / "MALCOMj"
    classes = malcomj / "build" / "classes" / "java" / "main"
    helper_class = classes / Path(*HELPER_CLASS.split(".")).with_suffix(".class")

    install_lib = malcomj / "build" / "install" / "MALCOMj" / "lib"
    install_jars = _jar_files(install_lib)
    if install_jars:
        entries = [classes, *install_jars] if helper_class.is_file() else install_jars
        return os.pathsep.join(str(path) for path in entries)

    cache_root = gradle_user_home
    if cache_root is None:
        configured = os.environ.get("GRADLE_USER_HOME")
        cache_root = Path(configured) if configured else Path.home() / ".gradle"
    modules = cache_root / "caches" / "modules-2" / "files-2.1"
    dependency_jars: list[Path] = []
    for group in ("org.eclipse.emfatic", "org.eclipse.emf", "org.eclipse.platform"):
        dependency_jars.extend(_jar_files(modules / group))

    if not helper_class.is_file() or not dependency_jars:
        raise FileNotFoundError(
            "EmfaticHelper runtime not found. Build MALCOMj with 'gradle installDist' "
            "or pass --gradle-user-home pointing to a populated Gradle cache."
        )
    return os.pathsep.join(str(path) for path in [classes, *dependency_jars])


class EmfaticSyntaxChecker:
    def __init__(
        self,
        repo_root: Path,
        java: str | None = None,
        classpath: str | None = None,
        gradle_user_home: Path | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.java = java or shutil.which("java")
        if not self.java:
            raise FileNotFoundError("Java was not found on PATH")
        self.classpath = classpath or discover_classpath(repo_root, gradle_user_home)
        self.timeout_seconds = timeout_seconds

    def check(self, path: Path) -> SyntaxCheck:
        result = subprocess.run(
            [self.java, "-cp", self.classpath, HELPER_CLASS, str(Path(path).resolve())],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise RuntimeError(f"EmfaticHelper failed for {path}: {detail}")
        try:
            payload = json.loads(result.stdout.strip())
        except json.JSONDecodeError as ex:
            raise RuntimeError(f"EmfaticHelper returned invalid JSON for {path}: {ex}") from ex

        errors = tuple(payload.get("errors", []))
        warnings = tuple(payload.get("warnings", []))
        builder_errors = tuple(str(item) for item in payload.get("builder_errors", []))
        return SyntaxCheck(
            syntax_ok=bool(payload.get("syntax_ok", False)),
            errors=errors,
            warnings=warnings,
            builder_errors=builder_errors,
        )
