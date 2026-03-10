import logging

from ._client import ConnectorClient, ConnectorError
from ._clients.office365 import Office365Client
from ._decorator import FunctionsConnectors
from ._models import ConnectorItem
from ._registration import register_connector_triggers
from ._triggers.office365 import Office365Email, Office365Event

__all__ = [
    "ConnectorClient",
    "ConnectorError",
    "ConnectorItem",
    "FunctionsConnectors",
    "Office365Client",
    "Office365Email",
    "Office365Event",
    "register_connector_triggers",
]

# Suppress noisy Azure SDK HTTP transport logs.
# Set at the root 'azure' logger to catch all SDK loggers before they're created.
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.storage").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
