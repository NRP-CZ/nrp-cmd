#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for files."""

from asyncio import TaskGroup
from functools import partial
from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client import limit_connections
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.files.table_formatters import format_files_table
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.cli.records.record_file_name import create_output_file_name
from nrp_cmd.config import Config

from ..arguments import (
    Output,
    with_config,
    with_output,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)


@async_command
@with_config
@with_repository
@with_resolved_vars("record_id")
@with_output
@with_verbosity
async def list_files(
    *,
    # generic options
    config: Config,
    repository: Optional[str] = None,
    # specific options
    record_id: Annotated[list[str], typer.Argument(help="Record ID(s)")],
    out: Output,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
) -> None:
    """Commandline client for listing files."""
    console = Console()

    with limit_connections(10):
        async with TaskGroup() as tg:
            for record_id in record_id:
                tg.create_task(
                    list_single_record(
                        record_id,
                        console,
                        config,
                        out.output,
                        out.output_format,
                        repository,
                        model,
                        published,
                        draft,
                        out.verbosity,
                    )
                )


async def list_single_record(
    record_id,
    console,
    config,
    output,
    output_format,
    repository,
    model,
    published,
    draft,
    verbosity,
):
    (
        record,
        record_id,
        repository_config,
        record_client,
        repository_client,
    ) = await read_record(record_id, repository, config, False, model, published, draft)
    files = await repository_client.files.list(record)

    if output:
        output = create_output_file_name(output, str(record.id), record, output_format)
        if output.parent:
            output.parent.mkdir(parents=True, exist_ok=True)

    with OutputWriter(
        output,
        output_format,
        console,
        partial(format_files_table, record, verbosity=verbosity),
    ) as printer:
        printer.output(files)
