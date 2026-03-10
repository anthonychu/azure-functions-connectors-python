import logging
import azure.functions as func
import azure.functions_connectors as fc

app = func.FunctionApp()

@fc.generic_connection_trigger(
    app,
    connection_id="%OFFICE365_CONNECTION_ID%",
    trigger_path="/Mail/OnNewEmail",
    trigger_queries={"folderPath": "Inbox"},
)
async def on_new_email(item: dict):
    subject = item.get("subject", "(no subject)")
    sender = item.get("from", {}).get("emailAddress", {}).get("name", "Unknown")
    logging.info(f"New email from {sender}: {subject}")


fc.register_connector_triggers(app)
