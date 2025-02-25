#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline interface for creating records."""

from asyncio import TaskGroup
from functools import partial
from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client import AsyncRecordsClient, get_async_client
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.base import set_variable as setvar
from nrp_cmd.cli.records.metadata import read_metadata
from nrp_cmd.cli.records.table_formatters import format_record_table
from nrp_cmd.config import Config
from nrp_cmd.progress import show_progress

from ..arguments import (
    Output,
    with_config,
    with_output,
    with_progress,
    with_repository,
    with_setvar,
    with_verbosity,
)


@async_command
@with_config
@with_output
@with_verbosity
@with_setvar
@with_repository
@with_progress
async def create_record(
    # generic options
    *,
    config: Config,
    out: Output,
    variable: Optional[str] = None,
    repository: Optional[str] = None,
    # command specific options
    metadata: Annotated[str, typer.Argument(help="Metadata")],
    files: Annotated[
        Optional[list[str]], typer.Argument(help="List of files to upload")
    ] = None,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    community: Annotated[Optional[str], typer.Option(help="Community name")] = None,
    workflow: Annotated[Optional[str], typer.Option(help="Workflow name")] = None,
    metadata_only: Annotated[
        bool,
        typer.Option("--metadata-only/", help="The record will only have metadata"),
    ] = False,
) -> None:
    """Create a new record in the repository and optionally upload files to it.

    Example:
    ```
    nrp-cmd create record '{"title": "My record"}' --set-variable var
        creates the record and stores its id in the variable var

    nrp-cmd create record '{"title": "My record"}' file1.txt '{"title": "File 1"}' file2.txt '{"title": "File 2"}'
        creates the record and uploads two files to it

    nrp-cmd create record '[{...},{...},{...}]' --set-variable var
        create multiple records and store their ids in the variable var
    ```

    """
    console = Console()
    if not files:
        files = []

    if len(files) % 2 != 0:
        raise ValueError("Files must be in pairs of <path> and file metadata.")

    metadata_json = read_metadata(metadata)
    client = await get_async_client(repository, config=config)
    records_api: AsyncRecordsClient = client.records

    if model is not None:
        records_api = records_api.with_model(model)

    if not isinstance(metadata_json, list):
        assert isinstance(metadata_json, dict), "Metadata must be a dictionary."
        metadata_json = [metadata_json]

    create_results = []
    assert isinstance(metadata_json, list)
    with show_progress(total=len(metadata_json), quiet=not out.progress):
        async with TaskGroup() as tg:
            for record_metadata in metadata_json:
                create_results.append(
                    tg.create_task(
                        records_api.create(
                            record_metadata,
                            community=community,
                            workflow=workflow,
                            files_enabled=not metadata_only,
                            model=model,
                        )
                    )
                )
    records = [result.result() for result in create_results]
    if variable:
        setvar(config, variable, [str(record.links.self_) for record in records])

    # upload files - imported here to avoid circular imports
    if files:
        if len(records) > 1:
            raise ValueError("Cannot upload files to multiple records.")

        record = records[0]
        from nrp_cmd.cli.files.upload import upload_files_to_record

        to_upload = list(zip(files[::2], files[1::2], strict=False))

        with show_progress(total=len(to_upload), quiet=not out.progress):
            async with TaskGroup() as tg:
                for file_, file_metadata in to_upload:
                    tg.create_task(
                        upload_files_to_record(client, record, (file_, file_metadata))
                    )

    with OutputWriter(
        out.output,
        out.output_format,
        console,
        partial(format_record_table, verbosity=out.verbosity),  # type: ignore # mypy does not understand this
    ) as printer:
        if len(records) == 1:
            printer.output(records[0])
        else:
            printer.multiple()
            for rec in records:
                printer.output(rec)
