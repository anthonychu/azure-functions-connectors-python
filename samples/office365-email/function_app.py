import logging
import azure.functions as func
import azure.functions_connectors as fc
from azure.functions_connectors import Office365Email

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)


@connectors.office365.on_new_email(
    connection_id="%OFFICE365_CONNECTION_ID%",
    folder="Inbox",
)
async def on_new_email(email: Office365Email):
    """Fires when a new email arrives in Inbox."""
    logging.info(f"[NEW EMAIL] From: {email.sender}")
    logging.info(f"[NEW EMAIL] Subject: {email.subject}")
    logging.info(f"[NEW EMAIL] Received: {email.received_at}")
    if email.body_preview:
        logging.info(f"[NEW EMAIL] Preview: {email.body_preview[:100]}")


@connectors.office365.on_flagged_email(
    connection_id="%OFFICE365_CONNECTION_ID%",
    folder="Inbox",
)
async def on_flagged_email(email: Office365Email):
    """Fires when an email is flagged in Inbox."""
    logging.info(f"[FLAGGED EMAIL] From: {email.sender}")
    logging.info(f"[FLAGGED EMAIL] Subject: {email.subject}")
    logging.info(f"[FLAGGED EMAIL] Received: {email.received_at}")
