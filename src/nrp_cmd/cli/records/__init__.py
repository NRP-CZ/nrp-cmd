#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for records."""

from .create import create_record
from .delete import delete_record
from .download import download_record
from .edit_record import edit_record
from .get import get_record
from .publish import publish_record
from .retract import retract_record
from .scan import scan_records
from .search import search_records
from .update import update_record
from .version_record import version_record

__all__ = (
    "download_record",
    "get_record",
    "search_records",
    "create_record",
    "scan_records",
    "update_record",
    "delete_record",
    "publish_record",
    "edit_record",
    "version_record",
    "retract_record",
)
