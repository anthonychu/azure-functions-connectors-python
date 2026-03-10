"""Typed Office 365 client for calling connector actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._client import ConnectorClient


class Office365Client:
    """Typed client for Office 365 connector actions.

    Usage::

        o365 = Office365Client(connector_client)
        await o365.send_email(to="user@company.com", subject="Hi", body="Hello!")
    """

    def __init__(self, client: ConnectorClient) -> None:
        self._client = client

    # ── Email ────────────────────────────────────────────────────────────

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        bcc: str | None = None,
        importance: str = "Normal",
    ) -> dict:
        """Send an email."""
        payload: dict = {
            "To": to,
            "Subject": subject,
            "Body": body,
            "Importance": importance,
        }
        if cc:
            payload["Cc"] = cc
        if bcc:
            payload["Bcc"] = bcc
        return await self._client.invoke("POST", "/v2/Mail", body=payload)

    async def get_emails(
        self,
        folder: str = "Inbox",
        top: int = 10,
        unread_only: bool = False,
        subject_filter: str | None = None,
        from_filter: str | None = None,
    ) -> list[dict]:
        """Get emails from a folder."""
        queries: dict[str, str] = {
            "folderPath": folder,
            "top": str(top),
            "fetchOnlyUnread": str(unread_only).lower(),
        }
        if subject_filter:
            queries["subjectFilter"] = subject_filter
        if from_filter:
            queries["from"] = from_filter
        result = await self._client.invoke("GET", "/v3/Mail", queries=queries)
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def get_email(self, message_id: str) -> dict:
        """Get a single email by ID."""
        return await self._client.invoke("GET", f"/v2/Mail/{message_id}")

    async def reply_to_email(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
    ) -> dict:
        """Reply to an email."""
        return await self._client.invoke(
            "POST",
            f"/v3/Mail/ReplyTo/{message_id}",
            body={"Body": body, "ReplyAll": reply_all},
        )

    async def forward_email(
        self,
        message_id: str,
        to: str,
        comment: str | None = None,
    ) -> dict:
        """Forward an email."""
        payload: dict = {"ToRecipients": to}
        if comment:
            payload["Comment"] = comment
        return await self._client.invoke(
            "POST",
            f"/codeless/v1.0/me/messages/{message_id}/forward",
            body=payload,
        )

    async def move_email(self, message_id: str, folder: str) -> dict:
        """Move an email to a folder."""
        return await self._client.invoke(
            "POST",
            f"/v2/Mail/Move/{message_id}",
            body={"folderPath": folder},
        )

    async def mark_as_read(self, message_id: str, is_read: bool = True) -> dict:
        """Mark an email as read or unread."""
        return await self._client.invoke(
            "PATCH",
            f"/codeless/v3/v1.0/me/messages/{message_id}/markAsRead",
            body={"isRead": is_read},
        )

    async def flag_email(self, message_id: str) -> dict:
        """Flag an email."""
        return await self._client.invoke(
            "POST",
            f"/codeless/v1.0/me/messages/{message_id}/flag",
            body={"flag": {"flagStatus": "flagged"}},
        )

    async def delete_email(self, message_id: str) -> dict:
        """Delete an email."""
        return await self._client.invoke(
            "DELETE",
            f"/codeless/v1.0/me/messages/{message_id}",
        )

    # ── Calendar ─────────────────────────────────────────────────────────

    async def get_events(self, calendar_id: str = "Calendar") -> list[dict]:
        """Get calendar events."""
        result = await self._client.invoke(
            "GET",
            f"/datasets/calendars/v4/tables/{calendar_id}/items",
        )
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def create_event(
        self,
        subject: str,
        start: str,
        end: str,
        timezone: str,
        calendar_id: str = "Calendar",
        body: str | None = None,
        location: str | None = None,
        required_attendees: str | None = None,
        show_as: str = "busy",
    ) -> dict:
        """Create a calendar event."""
        payload: dict = {
            "subject": subject,
            "start": start,
            "end": end,
            "timeZone": timezone,
            "showAs": show_as,
        }
        if body:
            payload["body"] = body
        if location:
            payload["location"] = location
        if required_attendees:
            payload["requiredAttendees"] = required_attendees
        return await self._client.invoke(
            "POST",
            f"/datasets/calendars/v4/tables/{calendar_id}/items",
            body=payload,
        )

    async def update_event(
        self,
        event_id: str,
        calendar_id: str = "Calendar",
        **fields,
    ) -> dict:
        """Update a calendar event. Pass fields as keyword args (subject, start, end, etc)."""
        return await self._client.invoke(
            "PATCH",
            f"/datasets/calendars/v4/tables/{calendar_id}/items/{event_id}",
            body=fields,
        )

    async def delete_event(self, event_id: str, calendar_id: str = "Calendar") -> dict:
        """Delete a calendar event."""
        return await self._client.invoke(
            "DELETE",
            f"/codeless/v1.0/me/calendars/{calendar_id}/events/{event_id}",
        )

    # ── Contacts ─────────────────────────────────────────────────────────

    async def get_contacts(self, folder: str = "Contacts") -> list[dict]:
        """Get contacts from a folder."""
        result = await self._client.invoke(
            "GET",
            f"/codeless/v1.0/me/contactFolders/{folder}/contacts",
        )
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        if isinstance(result, list):
            return result
        return []

    async def create_contact(
        self,
        given_name: str,
        surname: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        folder: str = "Contacts",
    ) -> dict:
        """Create a contact."""
        payload: dict = {"givenName": given_name}
        if surname:
            payload["surname"] = surname
        if email:
            payload["emailAddresses"] = [{"address": email}]
        if phone:
            payload["homePhones"] = [phone]
        return await self._client.invoke(
            "POST",
            f"/codeless/v1.0/me/contactFolders/{folder}/contacts",
            body=payload,
        )
