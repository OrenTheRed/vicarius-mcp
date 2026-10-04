"""Keep the harness independent of the machine it runs on."""

from __future__ import annotations

import json
import os


def isolate_environment() -> None:
    """Remove every VICARIUS_* and TYPESAFE_* setting, then define the one fake tenant the mock serves.

    The server applies VICARIUS_V2_TOOLSETS and VICARIUS_READ_ONLY when it is imported, so a value
    left over from the shell would silently shrink the tool list that the "all tools" run uses.
    Call this before anything imports the server.
    """
    for name in [n for n in os.environ if n.startswith(("VICARIUS", "TYPESAFE"))]:
        del os.environ[name]
    os.environ["VICARIUS_V2_TENANTS_FILE"] = "/nonexistent/vicarius-eval-tenants.json"
    os.environ["VICARIUS_V2_TENANTS"] = json.dumps({"acme": {"api_key": "dummy", "host": "acme.vicarius.cloud"}})
    os.environ["VICARIUS_V2_DEFAULT_TENANT"] = "acme"
