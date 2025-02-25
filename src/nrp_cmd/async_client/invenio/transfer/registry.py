#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Registry of known transfer types."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ....types.files import TRANSFER_TYPE_LOCAL, TRANSFER_TYPE_MULTIPART

if TYPE_CHECKING:
    from .base import Transfer



class TransferRegistry:
    """Registry of known transfer types."""

    def __init__(self):
        """Initialize the registry."""
        self.transfers = {}

    def register(self, transfer_type: str, transfer: type[Transfer]) -> None:
        """Register a transfer type.

        :param transfer_type:       transfer type
        :param transfer:            registered transfer
        """
        self.transfers[transfer_type] = transfer

    def get(self, transfer_type: str) -> Transfer:
        """Get a transfer for a transfer type.

        :param transfer_type:       transfer type
        :return:                    instance of a transfer
        """
        return self.transfers[transfer_type]()


transfer_registry = TransferRegistry()
"""Singleton for the transfer registry"""

#
# supported transfers are registered here
#
from .local import LocalTransfer  # noqa
from .multipart import MultipartTransfer  # noqa

transfer_registry.register(TRANSFER_TYPE_LOCAL, LocalTransfer)
transfer_registry.register(TRANSFER_TYPE_MULTIPART, MultipartTransfer)
