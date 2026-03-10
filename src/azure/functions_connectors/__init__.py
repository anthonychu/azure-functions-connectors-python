import logging

from ._decorator import generic_connection_trigger
from ._registration import register_connector_triggers

__all__ = ["generic_connection_trigger", "register_connector_triggers"]

# Suppress noisy Azure SDK HTTP transport logs.
# Set at the root 'azure' logger to catch all SDK loggers before they're created.
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.storage").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
