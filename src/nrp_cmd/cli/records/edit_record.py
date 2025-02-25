#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line client for editing published records."""

import asyncio
from functools import partial
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client.connection import limit_connections
from nrp_cmd.cli.base import OutputFormat, OutputWriter, async_command
from nrp_cmd.cli.records.record_file_name import create_output_file_name
from nrp_cmd.cli.records.table_formatters import format_record_table
from nrp_cmd.config import Config
from nrp_cmd.errors import DoesNotExistError
from nrp_cmd.types.records import Record
from nrp_cmd.types.requests import Request

from ..arguments import (
    Output,
    VerboseLevel,
    with_config,
    with_output,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)
from ..repository_requests.table_formatter import format_request_table
from .get import read_record


@async_command
@with_config
@with_repository
@with_resolved_vars("record_ids")
@with_output
@with_verbosity
async def edit_record(
    # generic options
    *,
    config: Config,
    repository: Optional[str],
    # specific options
    record_ids: Annotated[list[str], typer.Argument(help="Record ID")],
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    out: Output,
) -> None:
    """Edit published record's metadata."""
    console = Console()

    with limit_connections(10):
        tasks = []
        async with asyncio.TaskGroup() as tg:
            for record_id in record_ids:
                tasks.append(
                    tg.create_task(
                        edit_single_record(
                            record_id,
                            console,
                            config,
                            repository,
                            model,
                            out.output,
                            out.output_format,
                            out.verbosity,
                        )
                    )
                )
        results = [x.result() for x in tasks]
        for r in results:
            if r is None:
                raise typer.Abort()


async def edit_single_record(
    record_id: str,
    console: Console,
    config: Config,
    repository: str | None = None,
    model: str | None = None,
    output: Path | None = None,
    output_format: OutputFormat | None = None,
    verbosity: VerboseLevel = VerboseLevel.NORMAL,
) -> Record | Request | None:
    """Publish a record."""
    try:
        (
            record,
            final_record_id,
            repository_config,
            record_client,
            repository_client,
        ) = await read_record(
            record_id, repository, config, False, model, published=False, draft=True
        )
    except DoesNotExistError as e:
        console.print(f"[red]Record with id {record_id} does not exist.[/red]")
        if verbosity == VerboseLevel.VERBOSE:
            print(e)
        return None

    ret = await record_client.edit_metadata(record)

    if output:
        output = create_output_file_name(
            output, str(record.id or record_id or "unknown_id"), record, output_format
        )
    if output and output.parent:
        output.parent.mkdir(parents=True, exist_ok=True)

    # note: this is synchronous, but it is not a problem as only metadata are printed/saved
    if isinstance(ret, Record):
        with OutputWriter(
            output,
            output_format,
            console,
            partial(format_record_table, verbosity=verbosity),  # type: ignore # mypy does not understand this
        ) as printer:
            printer.output(ret)
    else:
        with OutputWriter(
            output,
            output_format,
            console,
            partial(format_request_table, verbosity=verbosity),  # type: ignore # mypy does not understand this
        ) as printer:
            printer.output(ret)

    return ret
        
