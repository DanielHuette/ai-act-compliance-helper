"""Single source of truth for data directory locations.

Context: the source tree, a frozen bundle and an installed wheel store the data in different
places, so every module asks here instead of deriving paths from its own file location. |
Input: COMPLIANCE_HELPER_ROOT, sys._MEIPASS, the source tree, the wheel's data directory |
Output: Paths to data, rules, cases, processed and raw directories.
"""

from __future__ import annotations

import os
import sys
import sysconfig
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

#: Folder under ``<prefix>/share`` where the wheel installs data and web (pyproject data-files).
INSTALLED_DATA_FOLDER = "ai-act-compliance-helper"


def installed_roots() -> Iterator[Path]:
    """Folders where pip puts the wheel's data files: the environment, then the user scheme."""
    schemes = (sysconfig.get_default_scheme(), sysconfig.get_preferred_scheme("user"))
    for scheme in dict.fromkeys(schemes):
        yield Path(sysconfig.get_path("data", scheme)) / "share" / INSTALLED_DATA_FOLDER


def _candidates() -> Iterator[Path]:
    requested = os.environ.get("COMPLIANCE_HELPER_ROOT")
    if requested:
        yield Path(requested)
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        yield Path(bundle_dir)
    yield Path(__file__).resolve().parents[2]
    yield from installed_roots()


@lru_cache(maxsize=1)
def root() -> Path:
    """Directory containing "data".

    Lookup order: COMPLIANCE_HELPER_ROOT (operator-maintained data), the PyInstaller bundle
    directory (sys._MEIPASS), the source tree root, then the data installed with the wheel.
    Without any of them the source tree root is returned, so the eventual "missing" message
    names a checkable path.
    """
    for candidate in _candidates():
        if (candidate / "data").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return root() / "data"


def rules_dir() -> Path:
    return data_dir() / "rules"


def cases_dir() -> Path:
    return data_dir() / "cases"


def processed_dir() -> Path:
    return data_dir() / "processed"


def raw_dir() -> Path:
    return data_dir() / "raw"
