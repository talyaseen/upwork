"""Hard isolation of this PUBLIC demo's OpenJarvis from any other instance.

OpenJarvis derives its ENTIRE config/memory/traces/telemetry/learning/vault
directory from the ``OPENJARVIS_HOME`` environment variable (precedence:
``OPENJARVIS_HOME`` > ``XDG_DATA_HOME/openjarvis`` > ``~/.openjarvis``).
OpenJarvis may also be used by other instances on this host, so this demo must
NEVER read or write the shared ``~/.openjarvis`` home.

We pin ``OPENJARVIS_HOME`` to a DEMO-ONLY directory BEFORE any OpenJarvis import.
Combined with the fact that the demo uses only the stateless engine API (which
takes the model host directly and touches no memory/traces/learning under the
home), this guarantees zero cross-contamination. Each instance also runs in its
own LXC (separate filesystems), so this is defense in depth.
"""

from __future__ import annotations

import logging
import os

from app.core.config import Settings

logger = logging.getLogger("app.isolation")


def configure_openjarvis_isolation(settings: Settings) -> str:
    """Pin OPENJARVIS_HOME to a demo-only dir. Returns the path actually used.

    Must run before the first ``import openjarvis``. Idempotent.
    """
    primary = settings.openjarvis_home
    fallback = settings.openjarvis_home_fallback
    chosen = primary
    try:
        os.makedirs(primary, exist_ok=True)
    except OSError:
        # /run may be read-only or unavailable (local dev); use the fallback.
        chosen = os.path.abspath(fallback)
        os.makedirs(chosen, exist_ok=True)
    os.environ["OPENJARVIS_HOME"] = chosen
    # Also pin XDG so nothing falls through to a shared XDG_DATA_HOME.
    os.environ.setdefault("XDG_DATA_HOME", os.path.dirname(chosen) or chosen)
    logger.info("OpenJarvis isolated to demo home: %s", chosen)
    return chosen
