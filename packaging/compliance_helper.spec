# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the Windows, macOS and Linux packages.

Context: one spec builds all three platforms; the 2.3 GB search model and torch stay out because
the classification does not need them, and so do the search indexes, which are useless without
that model; the service builds a fallback index per language at start. | Input: corpus, rules,
cases, web UI and packaging/launch_app.py | Output: dist/ComplianceHelper (plus
ComplianceHelper.app on macOS).
"""

from pathlib import Path

root = Path(SPECPATH).parent

data_files = [
    (str(root / "data" / "processed" / "corpus.jsonl"), "data/processed"),
    (str(root / "data" / "processed" / "corpus_report.json"), "data/processed"),
    (str(root / "data" / "processed" / "corpus.en.jsonl"), "data/processed"),
    (str(root / "data" / "processed" / "corpus_report.en.json"), "data/processed"),
    (str(root / "data" / "rules"), "data/rules"),
    (str(root / "data" / "cases"), "data/cases"),
    (str(root / "src" / "compliance_helper" / "webui"), "compliance_helper/webui"),
    (str(root / "src" / "compliance_helper" / "locales"), "compliance_helper/locales"),
    (str(root / "web"), "web"),
]

analysis = Analysis(
    [str(root / "packaging" / "launch_app.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "compliance_helper.service.app",
        "compliance_helper.classification.question_flow",
        "compliance_helper.classification.assessor",
    ],
    hookspath=[],
    runtime_hooks=[],
    # Full-text search libraries are fetched on demand, not bundled.
    excludes=["torch", "sentence_transformers", "FlagEmbedding", "transformers",
              "matplotlib", "scipy", "pandas", "tkinter", "PyQt5", "PySide6"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ComplianceHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="ComplianceHelper",
)

# Without an .app bundle macOS cannot move the app to Applications or show it in Launchpad.
import sys as _sys

if _sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ComplianceHelper.app",
        icon=None,
        bundle_identifier="dev.speedofthespirit.compliancehelper",
        info_plist={
            "CFBundleName": "ComplianceHelper",
            "CFBundleDisplayName": "AI Act Compliance Helper",
            "CFBundleDevelopmentRegion": "en",
            "CFBundleShortVersionString": "2.0.0",
            "NSHighResolutionCapable": True,
            # States explicitly why a legal tool opens a port: only 127.0.0.1 is used. One
            # bilingual text, because the bundle carries no per-language resource folders.
            "NSLocalNetworkUsageDescription":
                "The helper opens its interface in the browser on this computer; no data is sent "
                "to the network. / Der Helfer öffnet die Bedienoberfläche im Browser auf diesem "
                "Rechner; es werden keine Daten ins Netz gesendet.",
        },
    )
