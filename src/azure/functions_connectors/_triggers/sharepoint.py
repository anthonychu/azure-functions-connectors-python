"""Strongly-typed SharePoint connector triggers and item models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable
from urllib.parse import quote

from .._env import resolve_value
from .._models import ConnectorItem

if TYPE_CHECKING:
    from .._decorator import FunctionsConnectors


def _double_encode(url: str) -> str:
    return quote(quote(resolve_value(url), safe=""), safe="")


def _extract_person(value) -> str:
    if isinstance(value, dict):
        return (
            value.get("DisplayName")
            or value.get("displayName")
            or value.get("Email")
            or value.get("email")
            or value.get("Claims")
            or value.get("claims")
            or ""
        )
    if value is None:
        return ""
    return str(value)


class SharePointItem(ConnectorItem):
    """Typed wrapper for a SharePoint list item."""

    @property
    def id(self) -> str:
        return self.get("ID") or self.get("Id") or self.get("id", "")

    @property
    def title(self) -> str:
        return self.get("Title") or self.get("title", "")

    @property
    def created(self) -> str:
        return self.get("Created") or self.get("created", "")

    @property
    def modified(self) -> str:
        return self.get("Modified") or self.get("modified", "")

    @property
    def author(self) -> str:
        return _extract_person(self.get("Author"))

    @property
    def editor(self) -> str:
        return _extract_person(self.get("Editor"))

    @property
    def etag(self) -> str:
        return self.get("@odata.etag") or self.get("OData__x0040_odata_x002e_etag", "")

    @property
    def internal_id(self) -> str:
        return self.get("ItemInternalId", "")


class SharePointFile(SharePointItem):
    """Typed wrapper for a SharePoint file item."""

    @property
    def name(self) -> str:
        return self.get("{Name}") or self.get("FileLeafRef", "")

    @property
    def path(self) -> str:
        return self.get("{Path}") or self.get("FileDirRef") or self.get("FileRef", "")

    @property
    def size(self):
        return self.get("{FileSizeDisplay}") or self.get("File_x0020_Size", "")

    @property
    def content_type(self):
        return self.get("{ContentType}") or self.get("ContentType", "")


class SharePointTriggers:
    """Strongly-typed SharePoint trigger decorators and client factory."""

    def __init__(self, parent: FunctionsConnectors) -> None:
        self._parent = parent

    def get_client(self, connection_id: str) -> "SharePointClient":
        """Get a typed SharePoint client for calling actions."""
        from .._client import ConnectorClient
        from .._clients.sharepoint import SharePointClient

        return SharePointClient(ConnectorClient(connection_id))

    def new_item_trigger(
        self,
        connection_id: str,
        site_url: str,
        list_id: str,
    ) -> Callable:
        """Trigger when new items are created in a SharePoint list."""
        encoded_site = _double_encode(site_url)
        resolved_list_id = resolve_value(list_id)
        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/datasets/{encoded_site}/tables/{resolved_list_id}/onnewitems",
            trigger_queries={},
        )

    def updated_item_trigger(
        self,
        connection_id: str,
        site_url: str,
        list_id: str,
    ) -> Callable:
        """Trigger when items are updated in a SharePoint list."""
        encoded_site = _double_encode(site_url)
        resolved_list_id = resolve_value(list_id)
        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/datasets/{encoded_site}/tables/{resolved_list_id}/onupdateditems",
            trigger_queries={},
        )

    def new_file_trigger(
        self,
        connection_id: str,
        site_url: str,
        library_id: str,
    ) -> Callable:
        """Trigger when new files are created in a SharePoint document library."""
        encoded_site = _double_encode(site_url)
        resolved_library_id = resolve_value(library_id)
        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/datasets/{encoded_site}/tables/{resolved_library_id}/onnewfileitems",
            trigger_queries={},
        )

    def updated_file_trigger(
        self,
        connection_id: str,
        site_url: str,
        library_id: str,
    ) -> Callable:
        """Trigger when files are updated in a SharePoint document library."""
        encoded_site = _double_encode(site_url)
        resolved_library_id = resolve_value(library_id)
        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/datasets/{encoded_site}/tables/{resolved_library_id}/onupdatedfileitems",
            trigger_queries={},
        )
