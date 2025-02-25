#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for updating metadata of files."""

from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client import limit_connections
from nrp_cmd.cli.base import async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.config import Config

from ..arguments import (
    Output,
    VerboseLevel,
    with_config,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)


@async_command
@with_config
@with_repository
@with_resolved_vars("record_id")
@with_verbosity
async def delete_file(
    *,
    # generic options
    config: Config,
    repository: Optional[str] = None,
    out: Output,
    # specific options
    record_id: Annotated[str, typer.Argument(help="Record ID")],
    key: Annotated[str, typer.Argument(help="Key for the file")],
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
) -> None:
    """Delete a file in a record."""
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

        files_client = repository_client.files
        await files_client.delete(record, key)

    if out.verbosity != VerboseLevel.QUIET:
        console.print(f"[green]Deleted file {key} in record {record_id}.[/green]")