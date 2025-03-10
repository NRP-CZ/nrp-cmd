#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Table formatters for files."""

from collections.abc import Generator
from typing import Any

from rich import box
from rich.table import Table

from nrp_cmd.converter import converter
from nrp_cmd.types.files import File
from nrp_cmd.types.records import Record

from ..arguments import VerboseLevel


def format_files_table(
    record: Record, data: list[File], verbosity: VerboseLevel, **kwargs: Any
) -> Generator[Table, None, None] | Generator[str, None, None]:
    """Format the files table."""
    if verbosity == VerboseLevel.QUIET:
        yield "\n".join(sorted([file.key for file in data]))
    elif verbosity == VerboseLevel.VERBOSE:
        for file in sorted(data, key=lambda f: f.key):
            table = Table(f"File {file.key} @ record {record.links.self}", box=box.SIMPLE, title_justify="left")
            table.add_row("Key", file.key)
            table.add_row("Status", file.status)
            table.add_row("Mimetype", file.mimetype)
            table.add_row("Access", str(file.access))
            table.add_row("Metadata", str(file.metadata))
            table.add_row("Size", str(file.size))
            for link_name, link in converter.unstructure(file.links).items():
                table.add_row(link_name, str(link))
            yield table
    else:
        table = Table("Key", "Size", "Content", box=box.SIMPLE, title_justify="left")
        for file in sorted(data, key=lambda f: f.key):
            table.add_row(file.key, str(file.size), str(file.links.content))
        yield table
