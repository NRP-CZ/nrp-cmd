#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for updating metadata of files."""

from typing import Optional

from rich.console import Console

from nrp_cmd.async_client import limit_connections
from nrp_cmd.cli.base import async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.config import Config

from ..arguments import (
    Model,
    Output,
    VerboseLevel,
    argument_with_help,
    with_config,
    with_model,
    with_output,
    with_repository,
    with_resolved_vars,
)


@with_config
@with_repository
@with_resolved_vars("record_id")
@with_output
@with_model
@argument_with_help("record_id", type=str, help="Record ID")
@argument_with_help("key", type=str, help="Key for the file")
@async_command
async def delete_file(
    *,
    config: Config,
    repository: Optional[str] = None,
    out: Output,
    record_id: str,
    key: str,
    model: Model,
) -> None:
    """Delete a file in a record."""
    console = Console()

    with limit_connections(10):
        (
            record,
            record_id_url,
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

        files_client = repository_client.files
        await files_client.delete(record, key)

    if out.verbosity != VerboseLevel.QUIET:
        console.print(f"[green]Deleted file {key} in record {record_id_url}.[/green]")
