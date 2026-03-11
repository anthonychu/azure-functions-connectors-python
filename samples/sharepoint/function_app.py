"""SharePoint sample — triggers and client usage."""

import logging

import azure.functions as func
import azure.functions_connectors as fc
from azure.functions_connectors import SharePointFile, SharePointItem

app = func.FunctionApp()
connectors = fc.FunctionsConnectors(app)


@connectors.sharepoint.new_item_trigger(
    connection_id="%SHAREPOINT_CONNECTION_ID%",
    site_url="%SHAREPOINT_SITE_URL%",
    list_id="%SHAREPOINT_LIST_ID%",
)
async def on_new_list_item(item: SharePointItem):
    logging.info(f"[NEW LIST ITEM] id={item.id} title={item.title}")
    logging.info(f"[NEW LIST ITEM] author={item.author} created={item.created}")


@connectors.sharepoint.updated_file_trigger(
    connection_id="%SHAREPOINT_CONNECTION_ID%",
    site_url="%SHAREPOINT_SITE_URL%",
    library_id="%SHAREPOINT_LIBRARY_ID%",
)
async def on_updated_file(file_item: SharePointFile):
    logging.info(f"[UPDATED FILE] id={file_item.id} name={file_item.name}")
    logging.info(f"[UPDATED FILE] path={file_item.path} modified={file_item.modified}")


@app.timer_trigger(schedule="0 */10 * * * *", arg_name="timer", run_on_startup=True)
async def query_sharepoint(timer: func.TimerRequest):
    client = connectors.sharepoint.get_client("%SHAREPOINT_CONNECTION_ID%")
    sites = await client.get_sites()
    logging.info(f"[GET SITES] keys={list(sites.keys()) if isinstance(sites, dict) else []}")

    items = await client.get_items(
        site_url="%SHAREPOINT_SITE_URL%",
        list_id="%SHAREPOINT_LIST_ID%",
        top=5,
    )
    value = items.get("value", []) if isinstance(items, dict) else []
    logging.info(f"[GET ITEMS] fetched={len(value)}")
