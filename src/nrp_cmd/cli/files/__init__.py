#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for files."""

from .delete import delete_file
from .download import download_files
from .list import list_files
from .update import update_file_metadata
from .upload import upload_files

__all__ = ("list_files", "download_files", "upload_files", "update_file_metadata",
           "delete_file")
