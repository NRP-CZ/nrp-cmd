#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Helper functions for working with metadata on commandline."""

import json
import sys
from pathlib import Path
from typing import Any


class MetadataIsNotJSON(Exception):
    """Raised when metadata is not a valid JSON object."""


def read_metadata(metadata: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Read metadata from a string.

    If the string is '-', read metadata from stdin.
    If the string is a path to a file, read metadata from the file.
    If the metadata look like a JSON object, parse it as JSON.
    Otherwise raises an MetadataIsNotJSON exception.
    """
    if metadata == "-":
        # read metadata from stdin
        metadata = sys.stdin.read()

    metadata = metadata.strip()
    if not (metadata.startswith("{") or metadata.startswith("[")):
        pth = Path(metadata)
        if pth.exists():
            # metadata is path on filesystem
            metadata = pth.read_text()
        else:
            raise MetadataIsNotJSON(
                "Metadata must be a stringified JSON object or path to an existing file."
            )

    return json.loads(metadata)
