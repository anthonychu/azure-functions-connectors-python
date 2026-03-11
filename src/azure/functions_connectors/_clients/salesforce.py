"""Typed Salesforce client for calling connector actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._env import resolve_value

if TYPE_CHECKING:
    from .._client import ConnectorClient


class SalesforceClient:
    """Typed client for Salesforce connector actions."""

    def __init__(self, client: ConnectorClient) -> None:
        self._client = client

    async def get_records(
        self,
        table: str,
        filter: str | None = None,
        orderby: str | None = None,
        select: str | None = None,
        top: int | None = None,
    ) -> dict:
        """Get records from a Salesforce object table."""
        resolved_table = resolve_value(table)
        queries: dict[str, str] = {}
        if filter is not None:
            queries["$filter"] = filter
        if orderby is not None:
            queries["$orderby"] = orderby
        if select is not None:
            queries["$select"] = select
        if top is not None:
            queries["$top"] = str(top)
        return await self._client.invoke(
            "GET",
            f"/datasets/default/tables/{resolved_table}/items",
            queries=queries or None,
        )

    async def get_record(self, table: str, record_id: str) -> dict:
        """Get a single Salesforce record by ID."""
        resolved_table = resolve_value(table)
        resolved_record_id = resolve_value(record_id)
        return await self._client.invoke(
            "GET",
            f"/v2/datasets/default/tables/{resolved_table}/items/{resolved_record_id}",
        )

    async def create_record(self, table: str, record: dict) -> dict:
        """Create a Salesforce record."""
        resolved_table = resolve_value(table)
        return await self._client.invoke(
            "POST",
            f"/v2/datasets/default/tables/{resolved_table}/items",
            body=record,
        )

    async def update_record(self, table: str, record_id: str, updates: dict) -> dict:
        """Update a Salesforce record."""
        resolved_table = resolve_value(table)
        resolved_record_id = resolve_value(record_id)
        return await self._client.invoke(
            "PATCH",
            f"/v3/datasets/default/tables/{resolved_table}/items/{resolved_record_id}",
            body=updates,
        )

    async def delete_record(self, table: str, record_id: str) -> dict:
        """Delete a Salesforce record."""
        resolved_table = resolve_value(table)
        resolved_record_id = resolve_value(record_id)
        return await self._client.invoke(
            "DELETE",
            f"/datasets(default)/tables({resolved_table})/items({resolved_record_id})",
        )

    async def get_accounts(self, filter: str | None = None) -> dict:
        """Get Account records."""
        queries = {"$filter": filter} if filter is not None else None
        return await self._client.invoke(
            "GET",
            "/datasets/default/tables/account/items",
            queries=queries,
        )

    async def get_contacts(self, filter: str | None = None) -> dict:
        """Get Contact records."""
        queries = {"$filter": filter} if filter is not None else None
        return await self._client.invoke(
            "GET",
            "/datasets/default/tables/contact/items",
            queries=queries,
        )

    async def get_leads(self, filter: str | None = None) -> dict:
        """Get Lead records."""
        queries = {"$filter": filter} if filter is not None else None
        return await self._client.invoke(
            "GET",
            "/datasets/default/tables/lead/items",
            queries=queries,
        )

    async def get_opportunities(self, filter: str | None = None) -> dict:
        """Get Opportunity records."""
        queries = {"$filter": filter} if filter is not None else None
        return await self._client.invoke(
            "GET",
            "/datasets/default/tables/opportunity/items",
            queries=queries,
        )

    async def get_cases(self, filter: str | None = None) -> dict:
        """Get Case records."""
        queries = {"$filter": filter} if filter is not None else None
        return await self._client.invoke(
            "GET",
            "/datasets/default/tables/case/items",
            queries=queries,
        )

    async def execute_soql(self, query: str) -> dict:
        """Execute a SOQL query."""
        return await self._client.invoke(
            "POST",
            "/soql/executesoqlquery",
            body={"queryString": query},
        )

    async def create_bulk_job(
        self,
        table: str,
        operation: str,
        content_type: str = "CSV",
    ) -> dict:
        """Create a Salesforce bulk API job."""
        resolved_table = resolve_value(table)
        return await self._client.invoke(
            "POST",
            "/bulk/createjob",
            body={
                "object": resolved_table,
                "operation": operation,
                "contentType": content_type,
            },
        )

    async def get_tables(self) -> dict:
        """List available Salesforce object tables."""
        return await self._client.invoke("GET", "/datasets/default/tables")

    async def get_table_metadata(self, table: str) -> dict:
        """Get metadata for a Salesforce object table."""
        resolved_table = resolve_value(table)
        return await self._client.invoke(
            "GET",
            f"/$metadata.json/datasets/default/tables/{resolved_table}",
        )

    async def http_request(self, method: str, url: str, body: dict | None = None) -> dict:
        """Send a raw Salesforce HTTP request via connector proxy.

        Note: This action requires ``Method`` and ``Uri`` as HTTP headers,
        which may not work correctly through ``dynamicInvoke``. Use
        ``execute_soql`` or the typed CRUD methods instead when possible.
        """
        return await self._client.invoke(
            "POST",
            "/codeless/httprequest",
            queries={"Method": method, "Uri": url},
            body=body,
        )
