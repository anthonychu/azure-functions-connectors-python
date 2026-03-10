"""Compatibility shim — no longer needed.

``FunctionsConnectors(app)`` handles all registration.
This module is kept only so existing ``register_connector_triggers`` imports
don't break.  The function is a no-op.
"""

from __future__ import annotations


def register_connector_triggers(app=None, **kwargs) -> None:  # noqa: ARG001
    """No-op — kept for backward compatibility."""
    pass
