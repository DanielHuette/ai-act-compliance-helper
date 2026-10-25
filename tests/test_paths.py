"""Resolution of the data root in source tree, bundle and custom locations.

Context: a frozen bundle stores data elsewhere than the source tree, so paths.py must find it in
every layout. | Input: COMPLIANCE_HELPER_ROOT, sys._MEIPASS, the source tree | Output: pass when
every directory resolves under the expected root.
"""

from __future__ import annotations

import pytest

from compliance_helper import paths


@pytest.fixture(autouse=True)
def _clear_root_cache():
    """``root()`` is cached; clear it around every test."""
    paths.root.cache_clear()
    yield
    paths.root.cache_clear()


def test_rules_are_found_from_source_tree(root) -> None:
    assert paths.root() == root
    assert (paths.rules_dir() / "question_flow_layout.yaml").is_file()
    assert (paths.rules_dir() / "question_flow").is_dir()
    assert paths.cases_dir().is_dir()


def test_every_directory_is_under_data() -> None:
    for directory in (paths.rules_dir(), paths.cases_dir(), paths.processed_dir(), paths.raw_dir()):
        assert directory.parent == paths.data_dir()
    assert paths.data_dir().parent == paths.root()


def test_root_from_environment_takes_effect(tmp_path, monkeypatch) -> None:
    """A deployer maintaining their own rule set keeps it elsewhere."""
    (tmp_path / "data" / "rules").mkdir(parents=True)
    monkeypatch.setenv("COMPLIANCE_HELPER_ROOT", str(tmp_path))
    assert paths.root() == tmp_path
    assert paths.rules_dir() == tmp_path / "data" / "rules"


def test_directory_without_data_is_ignored(tmp_path, monkeypatch, root) -> None:
    """Otherwise an error message would point to an empty directory."""
    monkeypatch.setenv("COMPLIANCE_HELPER_ROOT", str(tmp_path / "does-not-exist"))
    assert paths.root() == root


def test_bundled_package_takes_precedence_over_source_tree(tmp_path, monkeypatch) -> None:
    """A bundle next to a source tree must use its own data from ``sys._MEIPASS``."""
    (tmp_path / "data" / "rules").mkdir(parents=True)
    monkeypatch.delenv("COMPLIANCE_HELPER_ROOT", raising=False)
    monkeypatch.setattr(paths.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.root() == tmp_path


def test_data_installed_with_the_wheel_is_found(tmp_path, monkeypatch) -> None:
    """Without a source tree, the data pip put under <prefix>/share must be used."""
    installed = tmp_path / "share" / paths.INSTALLED_DATA_FOLDER
    (installed / "data" / "rules").mkdir(parents=True)
    monkeypatch.delenv("COMPLIANCE_HELPER_ROOT", raising=False)
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "site-packages" / "pkg" / "paths.py"))
    monkeypatch.setattr(paths, "installed_roots", lambda: iter([installed]))
    assert paths.root() == installed
    assert paths.rules_dir() == installed / "data" / "rules"


def test_wheel_ships_every_runtime_file(root) -> None:
    """Rules, question flow, cases, corpora and the web pages must reach the installed package."""
    import tomllib

    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    data_files = pyproject["tool"]["setuptools"]["data-files"]
    shipped = {
        path.relative_to(root).as_posix()
        for patterns in data_files.values()
        for pattern in patterns
        for path in root.glob(pattern)
    }
    required = [
        *(root / "data" / "rules").glob("*.yaml"),
        *(root / "data" / "rules" / "question_flow").glob("*.yaml"),
        *(root / "data" / "cases").glob("*.yaml"),
        *(root / "data" / "processed").glob("corpus*.jsonl"),
        root / "web" / "index.html",
        root / "web" / "question_flow.json",
        root / "web" / "walkthrough.js",
        root / "web" / "page.js",
        *(root / "web" / "locales").glob("*.json"),
    ]
    missing = {path.relative_to(root).as_posix() for path in required} - shipped
    assert not missing
    for target, patterns in data_files.items():
        assert target.startswith(f"share/{paths.INSTALLED_DATA_FOLDER}/")
        for pattern in patterns:
            source_folder = pattern.rsplit("/", 1)[0]
            assert target.endswith(source_folder), (target, pattern)
