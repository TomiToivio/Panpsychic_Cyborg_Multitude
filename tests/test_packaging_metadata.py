from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_core_dependencies_do_not_include_zenoh() -> None:
    project = _pyproject()["project"]
    dependencies = project["dependencies"]
    assert not any("zenoh" in dependency.lower() for dependency in dependencies)


def test_zenoh_and_dev_are_explicit_extras() -> None:
    extras = _pyproject()["project"]["optional-dependencies"]
    assert any("eclipse-zenoh" in dependency.lower() for dependency in extras["zenoh"])
    assert any("pytest" in dependency.lower() for dependency in extras["dev"])


def test_console_entrypoint_is_packaged() -> None:
    scripts = _pyproject()["project"]["scripts"]
    assert scripts["multitude"] == "multitude.cli:main"
