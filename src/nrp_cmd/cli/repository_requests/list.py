#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line interface for getting records."""

from typing import Optional

from rich.console import Console

from nrp_cmd.async_client.connection import limit_connections
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.config import Config

from ..arguments import (
    Model,
    Output,
    argument_with_help,
    with_config,
    with_model,
    with_output,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)
from .table_formatter import (
    format_request_and_types_table,
)


@with_config
@with_repository
@with_model
@with_output
@with_verbosity
@with_resolved_vars("record_id")
@argument_with_help("record_id", type=str, help="Record ID")
@async_command
async def list_requests(
    *,
    config: Config,
    repository: Optional[str] = None,
    record_id: str,
    out: Output,
    model: Model,
) -> None:
    """Get a record from the repository."""
    console = Console()

    with limit_connections(10):
        (
            record,
            _final_record_id,
            _repository_config,
            _record_client,
            _repository_client,
        ) = await read_record(
            record_id,
            repository,
            config,
            True,
            model.model,
            model.published,
            model.draft,
        )

    with OutputWriter(
        out.output, out.output_format, console, format_request_and_types_table
    ) as printer:
        data = {
            "requests": [
                x for x in record.expanded.get("requests", [])
            ],
            "request_types": [
                x for x in record.expanded.get("request_types", [])
            ],
        }
        printer.output(data)
