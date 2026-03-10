"""Strongly-typed Office 365 connector triggers and item models."""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from .._models import ConnectorItem

if TYPE_CHECKING:
    from .._decorator import FunctionsConnectors


# ---------------------------------------------------------------------------
# Item models
# ---------------------------------------------------------------------------

class Office365Email(ConnectorItem):
    """Typed wrapper for an Office 365 email item."""

    @property
    def id(self) -> str:
        return self.get("Id", "")

    @property
    def subject(self) -> str:
        return self.get("Subject", "")

    @property
    def sender(self) -> str:
        return self.get("From", "")

    @property
    def to(self) -> str:
        return self.get("To", "")

    @property
    def cc(self) -> str | None:
        return self.get("Cc")

    @property
    def bcc(self) -> str | None:
        return self.get("Bcc")

    @property
    def body(self) -> str:
        return self.get("Body", "")

    @property
    def body_preview(self) -> str:
        return self.get("BodyPreview", "")

    @property
    def importance(self) -> int:
        return self.get("Importance", 0)

    @property
    def received_at(self) -> str:
        return self.get("DateTimeReceived", "")

    @property
    def has_attachment(self) -> bool:
        return self.get("HasAttachment", False)

    @property
    def is_read(self) -> bool:
        return self.get("IsRead", False)

    @property
    def is_html(self) -> bool:
        return self.get("IsHtml", False)

    @property
    def internet_message_id(self) -> str:
        return self.get("InternetMessageId", "")

    @property
    def conversation_id(self) -> str:
        return self.get("ConversationId", "")

    @property
    def attachments(self) -> list:
        return self.get("Attachments", [])

    @property
    def reply_to(self) -> str | None:
        return self.get("ReplyTo")


class Office365Event(ConnectorItem):
    """Typed wrapper for an Office 365 calendar event item."""

    @property
    def id(self) -> str:
        return self.get("Id", "")

    @property
    def subject(self) -> str:
        return self.get("Subject", "")

    @property
    def body(self) -> str:
        return self.get("Body", "")

    @property
    def body_preview(self) -> str:
        return self.get("BodyPreview", "")

    @property
    def start(self) -> str:
        return self.get("Start", "")

    @property
    def end(self) -> str:
        return self.get("End", "")

    @property
    def location(self) -> str:
        return self.get("Location", "")

    @property
    def organizer(self) -> str:
        return self.get("Organizer", "")

    @property
    def is_all_day(self) -> bool:
        return self.get("IsAllDay", False)

    @property
    def show_as(self) -> str:
        return self.get("ShowAs", "")

    @property
    def attendees(self) -> list:
        return self.get("Attendees", [])

    @property
    def is_reminder_on(self) -> bool:
        return self.get("IsReminderOn", False)

    @property
    def recurrence(self) -> str | None:
        return self.get("Recurrence")


# ---------------------------------------------------------------------------
# Trigger builder
# ---------------------------------------------------------------------------

class Office365Triggers:
    """Strongly-typed Office 365 trigger decorators.

    Accessed via ``connectors.office365``.
    """

    def __init__(self, parent: FunctionsConnectors) -> None:
        self._parent = parent

    def new_email_trigger(
        self,
        connection_id: str,
        folder: str = "Inbox",
        from_filter: str | None = None,
        to_filter: str | None = None,
        cc_filter: str | None = None,
        importance: str | None = None,
        subject_filter: str | None = None,
        include_attachments: bool = False,
        only_with_attachments: bool = False,
    ) -> Callable:
        """Trigger when a new email arrives."""
        queries: dict[str, str] = {"folderPath": folder}
        if from_filter:
            queries["from"] = from_filter
        if to_filter:
            queries["to"] = to_filter
        if cc_filter:
            queries["cc"] = cc_filter
        if importance:
            queries["importance"] = importance
        if subject_filter:
            queries["subjectFilter"] = subject_filter
        if include_attachments:
            queries["includeAttachments"] = "true"
        if only_with_attachments:
            queries["fetchOnlyWithAttachment"] = "true"

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path="/v3/Mail/OnNewEmail",
            trigger_queries=queries,
        )

    def flagged_email_trigger(
        self,
        connection_id: str,
        folder: str = "Inbox",
        from_filter: str | None = None,
        to_filter: str | None = None,
        importance: str | None = None,
        subject_filter: str | None = None,
    ) -> Callable:
        """Trigger when an email is flagged."""
        queries: dict[str, str] = {"folderPath": folder}
        if from_filter:
            queries["from"] = from_filter
        if to_filter:
            queries["to"] = to_filter
        if importance:
            queries["importance"] = importance
        if subject_filter:
            queries["subjectFilter"] = subject_filter

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path="/v4/Mail/OnFlaggedEmail",
            trigger_queries=queries,
        )

    def new_event_trigger(
        self,
        connection_id: str,
        calendar_id: str = "Calendar",
    ) -> Callable:
        """Trigger when a new calendar event is created."""
        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/datasets/calendars/v3/tables/{calendar_id}/onnewitems",
            trigger_queries={},
        )

    def event_changed_trigger(
        self,
        connection_id: str,
        calendar_id: str = "Calendar",
        incoming_days: int | None = None,
        past_days: int | None = None,
    ) -> Callable:
        """Trigger when a calendar event is added, updated, or deleted."""
        queries: dict[str, str] = {}
        if incoming_days is not None:
            queries["incomingDays"] = str(incoming_days)
        if past_days is not None:
            queries["pastDays"] = str(past_days)

        return self._parent.generic_trigger(
            connection_id=connection_id,
            trigger_path=f"/datasets/calendars/v3/tables/{calendar_id}/onchangeditems",
            trigger_queries=queries,
        )
