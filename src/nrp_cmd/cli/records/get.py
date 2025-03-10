#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line interface for getting records."""

import asyncio
from functools import partial
from pathlib import Path
from typing import Optional

import rich_click as click
from rich.console import Console
from yarl import URL

from nrp_cmd.async_client import (
    AsyncRecordsClient,
    AsyncRepositoryClient,
    get_async_client,
    get_repository_from_record_id,
)
from nrp_cmd.async_client.connection import AsyncConnection, limit_connections
from nrp_cmd.cli.base import OutputFormat, OutputWriter, async_command
from nrp_cmd.cli.records.record_file_name import create_output_file_name
from nrp_cmd.cli.records.table_formatters import format_record_table
from nrp_cmd.config import Config, RepositoryConfig
from nrp_cmd.errors import DoesNotExistError
from nrp_cmd.types.records import Record

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


@with_config
@with_repository
@with_record_ids
@with_output
@with_verbosity
@with_model
@click.option("--expand", is_flag=True, help="Expand the record")
@async_command
async def get_record(
    config: Config,
    repository: Optional[str],
    record_ids: list[str],
    out: Output,
    model: Model,
    expand: bool = False,
) -> None:
    """Get a record from the repository."""
    console = Console()

    with limit_connections(10):
        tasks: list[
            asyncio.Task[
                tuple[
                    Record | None,
                    Path | None,
                    RepositoryConfig | None,
                    AsyncRepositoryClient | None,
                ]
            ]
        ] = []
        async with asyncio.TaskGroup() as tg:
            for record_id in record_ids:
                tasks.append(
                    tg.create_task(
                        get_single_record(
                            record_id,
                            console,
                            config,
                            repository,
                            model.model,
                            out.output,
                            out.output_format,
                            model.published,
                            model.draft,
                            expand,
                            out.verbosity,
                        )
                    )
                )
        results = [x.result() for x in tasks]
        for r in results:
            if r[0] is None:
                raise click.Abort()


async def get_single_record(
    record_id: str,
    console: Console,
    config: Config,
    repository: str | None,
    model: str | None,
    output: Path | None,
    output_format: OutputFormat | None,
    published: bool,
    draft: bool,
    expand: bool,
    verbosity: VerboseLevel,
) -> tuple[
    Record | None, Path | None, RepositoryConfig | None, AsyncRepositoryClient | None
]:
    """Get a single record from the repository and print/save it."""
    try:
        (
            record,
            _final_record_id,
            repository_config,
            _record_client,
            repository_client,
        ) = await read_record(
            record_id, repository, config, expand, model, published, draft
        )
    except DoesNotExistError as e:
        console.print(f"[red]Record with id {record_id} does not exist.[/red]")
        if verbosity == VerboseLevel.VERBOSE:
            print(e)
        return None, output, None, None

    if output:
        output = create_output_file_name(
            output, str(record.id or record_id or "unknown_id"), record, output_format
        )
    if output and output.parent:
        output.parent.mkdir(parents=True, exist_ok=True)

    # note: this is synchronous, but it is not a problem as only metadata are printed/saved
    with OutputWriter(
        output,
        output_format,
        console,
        partial(format_record_table, verbosity=verbosity),  # type: ignore # mypy does not understand this
    ) as printer:
        printer.output(record)

    return record, output, repository_config, repository_client


async def read_record(
    record_id: str,
    repository: str | None,
    config: Config,
    expand: bool,
    model: str | None,
    published: bool,
    draft: bool,
) -> tuple[
    Record, str | URL, RepositoryConfig, AsyncRecordsClient, AsyncRepositoryClient
]:
    """Read a record from the repository, returning the record, its id and the repository config."""
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
    query: dict[str, str] = {}
    if expand:
        query["expand"] = "true"

    record = await records_api.read(record_id=final_record_id, query=query)
    return record, final_record_id, repository_config, records_api, client
