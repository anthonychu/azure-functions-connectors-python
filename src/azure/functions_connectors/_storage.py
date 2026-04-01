"""Centralized storage client factory with managed identity support.

Supports three authentication modes for Azure Storage, determined by
environment variables:

1. **Connection string** — ``AzureWebJobsStorage`` is set.
2. **Identity-based** — ``AzureWebJobsStorage__blobServiceUri`` (and
   optionally ``__queueServiceUri``, ``__clientId``) are set.  Works with
   system-assigned MI, user-assigned MI, and local dev credentials
   (Azure CLI / VS Code).
3. **Neither** — raises ``ValueError`` with guidance.
"""

from __future__ import annotations

import os
import threading

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.queue.aio import QueueClient

_ENV_CONN_STR = "AzureWebJobsStorage"
_ENV_BLOB_URI = "AzureWebJobsStorage__blobServiceUri"
_ENV_QUEUE_URI = "AzureWebJobsStorage__queueServiceUri"
_ENV_CLIENT_ID = "AzureWebJobsStorage__clientId"

_lock = threading.Lock()
_blob_service_client: BlobServiceClient | None = None
_credential: DefaultAzureCredential | None = None


def _get_credential() -> DefaultAzureCredential:
    """Return a cached DefaultAzureCredential, optionally scoped to a
    user-assigned managed identity when ``__clientId`` is set."""
    global _credential
    if _credential is None:
        client_id = os.environ.get(_ENV_CLIENT_ID)
        kwargs = {}
        if client_id:
            kwargs["managed_identity_client_id"] = client_id
        _credential = DefaultAzureCredential(**kwargs)
    return _credential


def get_blob_service_client() -> BlobServiceClient:
    """Return a cached async :class:`BlobServiceClient`.

    Uses a connection string when ``AzureWebJobsStorage`` is set, otherwise
    falls back to identity-based auth via ``AzureWebJobsStorage__blobServiceUri``.
    """
    global _blob_service_client
    if _blob_service_client is not None:
        return _blob_service_client

    with _lock:
        if _blob_service_client is not None:
            return _blob_service_client

        conn_str = os.environ.get(_ENV_CONN_STR)
        if conn_str:
            _blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            return _blob_service_client

        blob_uri = os.environ.get(_ENV_BLOB_URI)
        if blob_uri:
            _blob_service_client = BlobServiceClient(blob_uri, credential=_get_credential())
            return _blob_service_client

    raise ValueError(
        "Azure Storage is not configured. Set either the "
        "'AzureWebJobsStorage' connection string or the identity-based "
        "settings 'AzureWebJobsStorage__blobServiceUri' (and optionally "
        "'AzureWebJobsStorage__queueServiceUri' and "
        "'AzureWebJobsStorage__clientId')."
    )


def get_queue_client(queue_name: str) -> QueueClient:
    """Create an async :class:`QueueClient` for *queue_name*.

    A new client is returned each call (callers are responsible for closing
    it).  The underlying credential is shared and cached.
    """
    conn_str = os.environ.get(_ENV_CONN_STR)
    if conn_str:
        return QueueClient.from_connection_string(conn_str, queue_name)

    queue_uri = os.environ.get(_ENV_QUEUE_URI)
    if queue_uri:
        account_url = queue_uri.rstrip("/")
        return QueueClient(
            account_url, queue_name, credential=_get_credential()
        )

    raise ValueError(
        "Azure Storage is not configured. Set either the "
        "'AzureWebJobsStorage' connection string or the identity-based "
        "settings 'AzureWebJobsStorage__queueServiceUri' (and optionally "
        "'AzureWebJobsStorage__clientId')."
    )
