#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for uploading files."""

from asyncio import Task, TaskGroup
from functools import partial
from pathlib import Path
from typing import Any, Optional

import rich_click as click
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
    Model,
    Output,
    argument_with_help,
    with_config,
    with_model,
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
    transfer_type: str = "L",
) -> list[File]:
    """Upload files to a record."""
    # convert files to pairs
    file_client = client.files

    tasks: list[Task[Any]] = []
    async with TaskGroup() as tg:
        for _file, metadata in files:
            metadata_json: dict[str, Any]
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
                elif isinstance(_file, (str, Path)):  # type: ignore
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


@with_config
@with_repository
@with_resolved_vars("record_id")
@with_output
@with_verbosity
@with_model
@with_progress
@argument_with_help("record_id", type=str, help="Record ID")
@argument_with_help("file", type=str, help="File to upload")
@argument_with_help("metadata", type=str, required=False, help="Metadata for the file")
@click.option("--key", type=str, help="Key for the file")
@click.option("--transfer-type", type=str, help="Transfer type")
@async_command
async def upload_files(
    *,
    config: Config,
    repository: Optional[str] = None,
    record_id: str,
    file: str,
    metadata: Optional[str] = None,
    key: Optional[str] = None,
    model: Model,
    transfer_type: Optional[str] = None,
    out: Output,
) -> None:
    """Upload a file to a record."""
    console = Console()
    with limit_connections(10):
        (
            record,
            _record_id,
            repository_config,
            _record_client,
            repository_client,
        ) = await read_record(
            record_id,
            repository,
            config,
            False,
            model.model,
            model.published,
            model.draft,
        )

        metadata = metadata or "{}"
        metadata_json = read_metadata(metadata)
        assert isinstance(metadata_json, dict), "Metadata must be a dictionary."
        if key:
            metadata_json["key"] = key
        with show_progress(total=1, quiet=not out.progress):
            if not transfer_type:
                assert repository_config.info, (
                    "Do not have info for this repository to get transfer type, "
                    "please specify it manually."
                )

                transfer_type = "M" if "M" in repository_config.info.transfers else "L"

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
