#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Synchronous client for the NRP Invenio repository - low level connection."""

from .connection import ConnectionMixin, SyncConnection, connection_unstructure_hook
from .limiter import limit_connections

__all__ = (
    "SyncConnection",
    "connection_unstructure_hook",
    "ConnectionMixin",
    "limit_connections",
)
