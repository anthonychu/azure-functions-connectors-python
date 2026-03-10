import logging
import azure.functions as func
import azure.functions_connectors as fc

app = func.FunctionApp()


def _log_email(label: str, item: dict):
    """Shared logging for email items."""
    subject = item.get("Subject", "(no subject)")
    sender = item.get("From", "Unknown")
    received = item.get("DateTimeReceived", "unknown")
    preview = item.get("BodyPreview", "")[:100]
    logging.info(f"[{label}] From: {sender}")
    logging.info(f"[{label}] Subject: {subject}")
    logging.info(f"[{label}] Received: {received}")
    if preview:
        logging.info(f"[{label}] Preview: {preview}")


@fc.generic_connection_trigger(
    app,
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_new_email(item: dict):
    """Fires when a new email arrives in Inbox."""
    _log_email("NEW EMAIL", item)


@fc.generic_connection_trigger(
    app,
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnFlaggedEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_flagged_email(item: dict):
    """Fires when an email is flagged in Inbox."""
    _log_email("FLAGGED EMAIL", item)


fc.register_connector_triggers(app)
