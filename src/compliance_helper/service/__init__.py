"""Web service package of the AI Act Compliance Helper.

Context: Public entry points of the HTTP service. | Input: none |
Output: ``build_app`` factory, the ready ``app`` for uvicorn, ``run_server`` for the CLI.
"""

from compliance_helper.service.app import app, build_app, run_server

__all__ = ["app", "build_app", "run_server"]
