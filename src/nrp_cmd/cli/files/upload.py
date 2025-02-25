#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for uploading files."""

from asyncio import TaskGroup
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client import AsyncRepositoryClient, limit_connections
from nrp_cmd.async_client.streams import DataSource, StdInDataSource
from nrp_cmd.async_client.streams.file import FileSource
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.files.table_formatters import format_files_table
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.cli.records.metadata import read_metadata
from nrp_cmd.cli.records.record_file_name import create_output_file_name
from nrp_cmd.config import Config
from nrp_cmd.progress import show_progress
from nrp_cmd.types.files import File
from nrp_cmd.types.records import Record

from ..arguments import (
    Output,
    with_config,
    with_output,
    with_progress,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)


async def upload_files_to_record(
    client: AsyncRepositoryClient,
    record: Record,
    *files: tuple[str | DataSource | Path, dict[str, Any] | str],
    transfer_type="L",
) -> list[File]:
    """Upload files to a record."""
    # convert files to pairs
    file_client = client.files

    tasks = []
    async with TaskGroup() as tg:
        for _file, metadata in files:
            if not isinstance(metadata, dict):
                metadata_json = read_metadata(metadata)
            else:
                metadata_json = metadata

            key = metadata_json.get("key")
            if _file == "-":
                _file = StdInDataSource()
                key = key or "stdin"
            elif not key and isinstance(_file, (str, Path)):
                key = Path(_file).name
            if not key:
                raise ValueError("Key must be provided for file")

            if transfer_type == "M":
                # only use multipart for larger files
                if isinstance(_file, DataSource):
                    fs = await _file.size()
                elif isinstance(_file, (str, Path)):
                    fs = await FileSource(_file).size()
                else:
                    raise ValueError("Invalid file source")

                if fs < 10_000_000:
                    transfer_type = "L"

            tasks.append(
                tg.create_task(
                    file_client.upload(
                        record,
                        key,
                        metadata_json,
                        _file,
                        transfer_type=transfer_type,
                        progress=key if True else None,
                    )
                )
            )
    return [t.result() for t in tasks]



@async_command
@with_config
@with_repository
@with_resolved_vars("record_id")
@with_output
@with_verbosity
@with_progress
async def upload_files(
    *,
    # generic options
    config: Config,
    repository: Optional[str] = None,
    # specific options
    record_id: Annotated[str, typer.Argument(help="Record ID")],
    file: Annotated[str, typer.Argument(help="File to upload")],
    metadata: Annotated[
        Optional[str], typer.Argument(help="Metadata for the file")
    ] = None,
    key: Annotated[Optional[str], typer.Option(help="Key for the file")] = None,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
    transfer_type: Annotated[Optional[str], typer.Option(help="Transfer type")] = None,
    out: Output,
) -> None:
    """Upload a file to a record."""
    console = Console()
    with limit_connections(10):
        (
            record,
            record_id,
            repository_config,
            record_client,
            repository_client,
        ) = await read_record(
            record_id, repository, config, False, model, published, draft
        )

        metadata = metadata or "{}"
        metadata_json = read_metadata(metadata)
        assert isinstance(metadata_json, dict), "Metadata must be a dictionary."
        if key:
            metadata_json["key"] = key
        with (
            show_progress(total=1, quiet=not out.progress),
        ):
            if not transfer_type:
                if "M" in repository_config.info.transfers:
                    transfer_type = "M"
                else:
                    transfer_type = "L"

            files = await upload_files_to_record(
                repository_client,
                record,
                (file, metadata_json),
                transfer_type=transfer_type,
            )

    if out.output:
        output = create_output_file_name(
            out.output, str(record.id), record, out.output_format
        )
        if output.parent:
            output.parent.mkdir(parents=True, exist_ok=True)
    else:
        output = None

    with OutputWriter(
        output,
        out.output_format,
        console,
        partial(format_files_table, record, verbosity=out.verbosity),
    ) as printer:
        printer.output(files)
