"""Strongly-typed Salesforce connector triggers and item model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from .._env import resolve_value
from .._models import ConnectorItem

if TYPE_CHECKING:
    from .._decorator import FunctionsConnectors


class SalesforceRecord(ConnectorItem):
    """Typed wrapper for a Salesforce record item."""

    @property
    def id(self) -> str:
        return self.get("Id") or self.get("id", "")

    @property
    def name(self) -> str:
        return self.get("Name") or self.get("name", "")

    @property
    def record_type(self) -> str:
        attributes = self.get("attributes", {})
        if isinstance(attributes, dict):
            value = attributes.get("type")
            if value is not None:
                return str(value)
        return ""

    @property
    def created_date(self) -> str:
        return self.get("CreatedDate") or self.get("createdDate", "")

    @property
    def last_modified_date(self) -> str:
        return self.get("LastModifiedDate") or self.get("lastModifiedDate", "")

    @property
    def owner_id(self) -> str:
        return self.get("OwnerId") or self.get("ownerId", "")


class SalesforceTriggers:
    """Strongly-typed Salesforce trigger decorators and client factory."""

    def __init__(self, parent: FunctionsConnectors) -> None:
        self._parent = parent

    def get_client(self, connection_id: str) -> "SalesforceClient":
        """Get a typed Salesforce client for calling actions."""
        from .._client import ConnectorClient
        from .._clients.salesforce import SalesforceClient

        return SalesforceClient(ConnectorClient(connection_id))

    def new_item_trigger(
        self,
        connection_id: str,
        table: str,
        filter: str | None = None,
        orderby: str | None = None,
        select: str | None = None,
        min_interval: int = 60,
        max_interval: int = 300,
    ) -> Callable:
        """Trigger when new records are created for a Salesforce object."""
        resolved_table = resolve_value(table)
        queries: dict[str, str] = {}
        if filter is not None:
            queries["$filter"] = filter
        if orderby is not None:
            queries["$orderby"] = orderby
        if select is not None:
            queries["$select"] = select

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/trigger/datasets/default/tables/{resolved_table}/onnewitems",
            trigger_queries=queries,
            min_interval=min_interval,
            max_interval=max_interval,
        )

    def updated_item_trigger(
        self,
        connection_id: str,
        table: str,
        filter: str | None = None,
        orderby: str | None = None,
        select: str | None = None,
        min_interval: int = 60,
        max_interval: int = 300,
    ) -> Callable:
        """Trigger when records are updated for a Salesforce object."""
        resolved_table = resolve_value(table)
        queries: dict[str, str] = {}
        if filter is not None:
            queries["$filter"] = filter
        if orderby is not None:
            queries["$orderby"] = orderby
        if select is not None:
            queries["$select"] = select

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/trigger/datasets/default/tables/{resolved_table}/onupdateditems",
            trigger_queries=queries,
            min_interval=min_interval,
            max_interval=max_interval,
        )

    def deleted_item_trigger(
        self,
        connection_id: str,
        table: str,
        filter: str | None = None,
        orderby: str | None = None,
        top: int | None = None,
        min_interval: int = 60,
        max_interval: int = 300,
    ) -> Callable:
        """Trigger when records are deleted for a Salesforce object."""
        resolved_table = resolve_value(table)
        queries: dict[str, str] = {}
        if filter is not None:
            queries["$filter"] = filter
        if orderby is not None:
            queries["$orderby"] = orderby
        if top is not None:
            queries["$top"] = str(top)

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/trigger/datasets/default/tables/{resolved_table}/ondeleteditems",
            trigger_queries=queries,
            min_interval=min_interval,
            max_interval=max_interval,
        )
