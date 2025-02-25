#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for updating metadata of files."""

from functools import partial
from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client import limit_connections
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.files.table_formatters import format_files_table
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.cli.records.metadata import read_metadata
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
async def update_file_metadata(
    *,
    # generic options
    config: Config,
    repository: Optional[str] = None,
    # specific options
    record_id: Annotated[str, typer.Argument(help="Record ID")],
    key: Annotated[str, typer.Argument(help="Key for the file")],
    metadata: Annotated[
        Optional[str], typer.Argument(help="Metadata for the file")
    ] = None,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
    out: Output,
) -> None:
    """Update the metadata of a file in a record."""
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
