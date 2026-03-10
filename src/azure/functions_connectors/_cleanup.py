"""Cleanup orphan trigger state blobs that no longer match registered triggers."""

from __future__ import annotations

import logging

from ._decorator import _active_connectors
from ._state import delete_state, list_state_ids

logger = logging.getLogger(__name__)


async def cleanup_orphan_states() -> None:
    """Delete state blobs whose instance_id has no matching registered trigger."""
    triggers = _active_connectors.get_registered_triggers() if _active_connectors else []
    registered_ids = {t.instance_id for t in triggers}
    persisted_ids = await list_state_ids()

    orphans = [sid for sid in persisted_ids if sid not in registered_ids]

    if not orphans:
        logger.debug("No orphan trigger states found")
        return

    for instance_id in orphans:
        await delete_state(instance_id)
        logger.info("Cleaned up orphan trigger state: %s", instance_id)
