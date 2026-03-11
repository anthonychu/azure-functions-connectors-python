"""Salesforce sample — triggers and client usage."""

import logging

import azure.functions as func
import azure.functions_connectors as fc
from azure.functions_connectors import SalesforceRecord

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)


@connectors.salesforce.new_item_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    table="contact",
)
async def on_new_contact(record: SalesforceRecord):
    logging.info(f"[NEW CONTACT] id={record.id} name={record.name}")


@connectors.salesforce.updated_item_trigger(
    connection_id="%SALESFORCE_CONNECTION_ID%",
    table="opportunity",
)
async def on_updated_opportunity(record: SalesforceRecord):
    logging.info(f"[UPDATED OPPORTUNITY] id={record.id} name={record.name}")
    logging.info(f"[UPDATED OPPORTUNITY] last_modified_date={record.last_modified_date}")


@app.timer_trigger(schedule="0 */10 * * * *", arg_name="timer", run_on_startup=True)
async def query_salesforce_records(timer: func.TimerRequest):
    client = connectors.salesforce.get_client("%SALESFORCE_CONNECTION_ID%")
    result = await client.get_contacts(filter="Name ne null")
    items = result.get("value", []) if isinstance(result, dict) else []
    logging.info(f"[QUERY CONTACTS] fetched={len(items)}")

