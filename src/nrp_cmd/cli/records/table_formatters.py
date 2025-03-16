#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Table formatters for records."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, Any

from rich import box
from rich.table import Table

from nrp_cmd.cli.base import write_table_row
from nrp_cmd.converter import converter

from ..arguments import VerboseLevel

if TYPE_CHECKING:
    from nrp_cmd.types.records import Record, RecordList


def format_search_table(
    data: RecordList, *, verbosity: VerboseLevel
) -> Generator[Table | str, None, None]:
    """Format a search result as a table."""
    table = Table(
        title="Records", box=box.SIMPLE, title_justify="left", show_header=False
    )
    table.add_row("Self", str(data.links.self_))
    table.add_row("Next", str(data.links.next))
    table.add_row("Previous", str(data.links.prev))
    table.add_row("Total", str(data.total))
    yield table

    for record in data:
        yield from format_record_table(record, verbosity=verbosity)


def format_record_table(
    data: Record,
    *,
    verbosity: VerboseLevel,
    **kwargs: Any,  # noqa: ANN401
) -> Generator[Table | str, None, None]:
    """Format a record as a table."""
    if verbosity == VerboseLevel.QUIET:
        yield str(data.links.self_)
    else:
        table = Table(f"Record {data.id}", box=box.SIMPLE, title_justify="left")
        record_dump = converter.unstructure(data)

        if verbosity == VerboseLevel.VERBOSE or "metadata" not in record_dump:
            for k, v in record_dump.items():
                if k != "metadata":
                    write_table_row(table, k, v)

        if "metadata" in record_dump:
            if verbosity == VerboseLevel.VERBOSE:
                table.add_row("Metadata", "")
                prefix = "    "
            else:
                prefix = ""
            for k, v in record_dump["metadata"].items():
                write_table_row(table, k, v, prefix=prefix)

        if verbosity != VerboseLevel.VERBOSE and "errors" in record_dump:
            error_table = Table(box=None, show_header=False)
            for err in record_dump["errors"]:
                error_table.add_row(
                    err["field"], "\n".join(str(x) for x in err["messages"])
                )
            table.add_row("Errors", error_table)

        yield table
