#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line interface for getting records."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client.connection import limit_connections
from nrp_cmd.cli.base import OutputFormat, OutputWriter, async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.config import Config

from ..arguments import with_config, with_repository, with_resolved_vars
from .table_formatter import (
    format_request_and_types_table,
)


@async_command
@with_config
@with_repository
@with_resolved_vars("record_id")
async def list_requests(
    *,
    # generic arguments
    config: Config,
    repository: Optional[str] = None,
    # specific arguments
    record_id: Annotated[str, typer.Argument(help="Record ID")],
    output: Annotated[
        Optional[Path], typer.Option("-o", help="Save the output to a file")
    ] = None,
    output_format: Annotated[
        Optional[OutputFormat],
        typer.Option("-f", help="The format of the output"),
    ] = None,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
) -> None:
    """Get a record from the repository."""
    console = Console()

    with limit_connections(10):
        (
            record,
            final_record_id,
            repository_config,
            record_client,
            repository_client,
        ) = await read_record(
            record_id, repository, config, True, model, published, draft
        )

    with OutputWriter(
        output, output_format, console, format_request_and_types_table
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
