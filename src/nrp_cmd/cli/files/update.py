#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for updating metadata of files."""

from functools import partial
from typing import Optional

from rich.console import Console

from nrp_cmd.async_client import limit_connections
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.files.table_formatters import format_files_table
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.cli.records.metadata import read_metadata
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


@with_config
@with_repository
@with_resolved_vars("record_id")
@with_output
@with_verbosity
@with_model
@argument_with_help("record_id", type=str, help="Record ID")
@argument_with_help("key", type=str, help="Key for the file")
@argument_with_help("metadata", type=str, required=False, help="Metadata for the file")
@async_command
async def update_file_metadata(
    *,
    config: Config,
    repository: Optional[str] = None,
    record_id: str,
    key: str,
    metadata: Optional[str] = None,
    model: Model,
    out: Output,
) -> None:
    """Update the metadata of a file in a record."""
    console = Console()

    with limit_connections(10):
        (
            record,
            _record_id,
            _repository_config,
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

        files_client = repository_client.files
        files = await files_client.list(record)
        file = next((f for f in files if f.key == key), None)

        if not file:
            raise ValueError(
                f"File with key {key} not found in record {record_id}: {", ".join([f.key for f in files])}"
            )

        file.metadata = metadata_json
        updated_file = await files_client.update(file)

    with OutputWriter(
        out.output,
        out.output_format,
        console,
        partial(format_files_table, record, verbosity=out.verbosity),  # type: ignore # mypy can not infer the corredct type of the partial function
    ) as printer:
        printer.output([updated_file])
