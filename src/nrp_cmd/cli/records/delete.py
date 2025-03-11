#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line interface for getting records."""

import asyncio
from typing import Optional

from rich.console import Console

from nrp_cmd.async_client import (
    AsyncRecordsClient,
    get_async_client,
    get_repository_from_record_id,
)
from nrp_cmd.async_client.connection import AsyncConnection, limit_connections
from nrp_cmd.cli.base import async_command
from nrp_cmd.config import Config

from ..arguments import (
    Model,
    Output,
    VerboseLevel,
    with_config,
    with_model,
    with_output,
    with_record_ids,
    with_repository,
    with_verbosity,
)


@with_model
@with_config
@with_repository
@with_record_ids
@with_output
@with_verbosity
@async_command
async def delete_record(
    config: Config,
    repository: Optional[str],
    out: Output,
    record_ids: list[str],
    model: Model,
) -> None:
    """Get a record from the repository."""
    console = Console()

    with limit_connections(10):
        async with asyncio.TaskGroup() as tg:
            for record_id in record_ids:
                tg.create_task(
                    delete_single_record(
                        record_id,
                        console,
                        config,
                        repository,
                        model.model,
                        model.published,
                        model.draft,
                        out.verbosity,
                    )
                )


async def delete_single_record(
    record_id: str,
    console: Console,
    config: Config,
    repository: str | None,
    model: str | None,
    published: bool,
    draft: bool,
    verbosity: VerboseLevel,
) -> None:
    """Get a single record from the repository and print/save it."""
    connection = AsyncConnection()
    
    final_record_id, repository_config = await get_repository_from_record_id(
        connection, record_id, config, repository
    )
    # set it temporarily to the config
    config.add_repository(repository_config)
    client = await get_async_client(repository, config=config)
    records_api: AsyncRecordsClient = client.records
    if model is not None:
        records_api = records_api.with_model(model)
    if published:
        records_api = records_api.published_records
    if draft:
        records_api = records_api.draft_records

    await records_api.delete(final_record_id)
    if verbosity != VerboseLevel.QUIET:
        console.print(f"[green]Record with id {record_id} has been deleted.[/green]")
