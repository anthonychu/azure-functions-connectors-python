"""Decorator for registering connector trigger handlers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

import azure.functions as func

from ._models import TriggerConfig, TriggerRegistration

logger = logging.getLogger(__name__)

_registered_triggers: list[TriggerRegistration] = []
# Maps queue_name → list of (handler, instance_id) for dispatch
_queue_handlers: dict[str, list[tuple[Callable, str]]] = {}
_timer_registered = False  # True once the shared timer is registered


def _queue_name_for(func_name: str) -> str:
    """Derive a queue name from the user's function name."""
    # Azure queue names: lowercase, alphanumeric + hyphens, 3-63 chars
    return f"ct-{func_name.replace('_', '-').lower()}"[:63]


def generic_connection_trigger(
    app: func.FunctionApp,
    connection_id: str,
    trigger_path: str,
    trigger_queries: dict[str, str] | None = None,
    min_interval: int = 60,
    max_interval: int = 300,
) -> Callable:
    """Register a function as a connector-trigger handler.

    Each decorated function gets its own queue and queue-triggered Azure Function.
    A shared timer function polls all triggers and enqueues items to per-handler queues.
    """

    if min_interval < 1:
        raise ValueError("min_interval must be >= 1")
    if max_interval < min_interval:
        raise ValueError(f"max_interval ({max_interval}) must be >= min_interval ({min_interval})")

    def decorator(user_func: Callable) -> Callable:
        global _timer_registered

        config = TriggerConfig(
            connection_id=connection_id,
            trigger_path=trigger_path,
            trigger_queries=trigger_queries or {},
            min_interval=min_interval,
            max_interval=max_interval,
        )
        registration = TriggerRegistration(config=config, handler=user_func)
        _registered_triggers.append(registration)

        # Each handler gets its own queue
        queue_name = _queue_name_for(user_func.__name__)
        _queue_handlers.setdefault(queue_name, []).append(
            (user_func, registration.instance_id)
        )

        # Register the shared timer on the FIRST decorator call
        if not _timer_registered:
            _timer_registered = True
            _register_timer(app)

        # Register a per-handler queue function
        _register_queue_function(app, user_func, queue_name)

        print(
            f"[azure.functions_connectors] Registered trigger: "
            f"{config.trigger_path} → {user_func.__name__} (queue: {queue_name})"
        )

        return user_func

    return decorator


def _register_timer(app: func.FunctionApp) -> None:
    """Register the shared poller timer function (once)."""
    from ._cleanup import cleanup_orphan_states
    from ._poller import poll_all_triggers

    cleanup_done = False

    @app.generic_trigger(
        arg_name="timer",
        type="timerTrigger",
        schedule="0 */1 * * * *",
        runOnStartup=True,
    )
    async def ConnectorTriggerPoller(timer) -> None:
        nonlocal cleanup_done
        if not cleanup_done:
            await cleanup_orphan_states()
            cleanup_done = True
        await poll_all_triggers()


def _register_queue_function(
    app: func.FunctionApp, user_func: Callable, queue_name: str
) -> None:
    """Register a queue-triggered function for a specific handler."""
    from ._poller import retrieve_item_blob

    # The function name in Azure Functions matches the user's function name
    func_name = user_func.__name__

    async def queue_processor(msg: func.QueueMessage) -> None:
        body = msg.get_body().decode("utf-8")
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            logger.error("[%s] Malformed queue message, dropping", func_name)
            return

        item = payload.get("item")
        if item is None:
            item_blob = payload.get("item_blob")
            if item_blob:
                item = await retrieve_item_blob(item_blob)
            else:
                logger.error("[%s] Missing item, dropping", func_name)
                return

        if asyncio.iscoroutinefunction(user_func):
            await user_func(item)
        else:
            user_func(item)

    # Set the function name so Azure Functions displays it correctly
    queue_processor.__name__ = func_name

    # Register via generic_trigger (avoids binding leakage)
    app.generic_trigger(
        arg_name="msg",
        type="queueTrigger",
        queueName=queue_name,
        connection="AzureWebJobsStorage",
    )(queue_processor)


def get_registered_triggers() -> list[TriggerRegistration]:
    """Return all registered trigger registrations."""
    return _registered_triggers


def get_queue_names_for_instance(instance_id: str) -> list[str]:
    """Return all queue names that should receive items for this instance_id."""
    queues = []
    for queue_name, handlers in _queue_handlers.items():
        for _, iid in handlers:
            if iid == instance_id:
                queues.append(queue_name)
    return queues
