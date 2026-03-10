"""Generic connector client for calling connector actions via dynamicInvoke."""

from __future__ import annotations

import json
import logging
import urllib.request

from azure.identity import DefaultAzureCredential

from ._env import resolve_value

logger = logging.getLogger(__name__)

_ARM_BASE = "https://management.azure.com"
_API_VERSION = "2016-06-01"


class ConnectorClient:
    """Call any connector action via ARM dynamicInvoke.

    Usage::

        client = ConnectorClient("/subscriptions/.../connections/office365")
        result = await client.invoke("POST", "/v2/Mail", body={"To": "...", ...})
    """

    def __init__(self, connection_id: str) -> None:
        self._connection_id = resolve_value(connection_id)

    async def invoke(
        self,
        method: str,
        path: str,
        queries: dict[str, str] | None = None,
        body: dict | None = None,
    ) -> dict:
        """Invoke a connector action.

        Returns the response body as a dict.
        Raises ``ConnectorError`` on non-success status.
        """
        import asyncio
        return await asyncio.to_thread(
            self._invoke_sync, method, path, queries, body
        )

    def _invoke_sync(
        self,
        method: str,
        path: str,
        queries: dict[str, str] | None,
        body: dict | None,
    ) -> dict:
        url = f"{_ARM_BASE}{self._connection_id}/dynamicInvoke?api-version={_API_VERSION}"

        request_body: dict = {
            "request": {
                "method": method.upper(),
                "path": path,
            }
        }
        if queries:
            request_body["request"]["queries"] = queries
        if body is not None:
            request_body["request"]["body"] = body

        encoded = json.dumps(request_body).encode()

        credential = DefaultAzureCredential()
        try:
            token = credential.get_token("https://management.azure.com/.default").token
        finally:
            credential.close()

        req = urllib.request.Request(
            url,
            data=encoded,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode() if exc.fp else ""
            raise ConnectorError(exc.code, f"dynamicInvoke failed: {exc.reason}", error_body) from exc

        inner = data.get("response", {})
        status_str = str(inner.get("statusCode", ""))
        status_ok = status_str in (
            "OK", "Created", "Accepted", "NoContent",
            "200", "201", "202", "204",
        )
        response_body = inner.get("body", {})

        if not status_ok:
            raise ConnectorError(
                status_str,
                f"Connector returned {status_str}",
                json.dumps(response_body) if response_body else "",
            )

        return response_body


class ConnectorError(Exception):
    """Error from a connector action invocation."""

    def __init__(self, status: str | int, message: str, body: str = "") -> None:
        self.status = status
        self.body = body
        super().__init__(message)
