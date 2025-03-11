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
from pathlib import Path
from typing import Optional

from rich.console import Console

from nrp_cmd.async_client import limit_connections
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.files.table_formatters import format_files_table
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.cli.records.record_file_name import create_output_file_name
from nrp_cmd.config import Config

from ..arguments import (
    Model,
    Output,
    OutputFormat,
    VerboseLevel,
    argument_with_help,
    with_config,
    with_model,
    with_output,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)


@with_config
@with_repository
@with_resolved_vars("record_ids")
@with_output
@with_verbosity
@with_model
@argument_with_help("record_ids", type=str, nargs=-1, help="Record ID(s)")
@async_command
async def list_files(
    *,
    config: Config,
    repository: Optional[str] = None,
    record_ids: list[str],
    out: Output,
    model: Model,
) -> None:
    """List record's files."""
    console = Console()

    with limit_connections(10):
        async with TaskGroup() as tg:
            for record_id in record_ids:
                tg.create_task(
                    list_single_record(
                        record_id,
                        console,
                        config,
                        out.output,
                        out.output_format,
                        repository,
                        model.model,
                        model.published,
                        model.draft,
                        out.verbosity,
                    )
                )


async def list_single_record(
    record_id: str,
    console: Console,
    config: Config,
    output: Optional[Path],
    output_format: Optional[OutputFormat],
    repository: Optional[str],
    model: Optional[str],
    published: bool,
    draft: bool,
    verbosity: VerboseLevel,
):
    """List and print single record files."""
    (
        record,
        _record_id_url,
        _repository_config,
        _record_client,
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
