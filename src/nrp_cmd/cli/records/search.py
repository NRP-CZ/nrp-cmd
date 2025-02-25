#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command-line interface for searching records."""

from functools import partial
from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client import AsyncRecordsClient, RecordStatus, get_async_client
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.base import set_variable as setvar
from nrp_cmd.config import Config

from ..arguments import (
    Output,
    with_config,
    with_output,
    with_repository,
    with_setvar,
    with_verbosity,
)
from .table_formatters import (
    format_search_table,
)


@async_command
@with_config
@with_repository
@with_output
@with_verbosity
@with_setvar
async def search_records(
    # generic options
    *,
    config: Config,
    repository: Optional[str] = None,
    # specific options
    query: Annotated[Optional[str], typer.Argument(help="Query string")] = None,
    variable: Optional[str] = None,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    community: Annotated[Optional[str], typer.Option(help="Community name")] = None,
    size: Annotated[
        int, typer.Option(help="Number of results to return on a page")
    ] = 10,
    page: Annotated[int, typer.Option(help="Page number")] = 1,
    sort: Annotated[Optional[str], typer.Option(help="Sort order")] = "bestmatch",
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
    out: Output,
) -> None:
    """Return a page of records inside repository that match the given query."""
    console = Console()

    records_api, args = await _prepare_search(
        community, config, model, page, published, query, repository, size, sort
    )

    record_list = await records_api.search(**args)

    if variable:
        urls = [str(record.links.self_) for record in record_list]
        setvar(config, variable, urls)

    with OutputWriter(
        out.output,
        out.output_format,
        console,
        partial(format_search_table, verbosity=out.verbosity),  # type: ignore # mypy does not understand this
    ) as printer:
        del record_list.aggregations
        printer.output(record_list)


async def _prepare_search(
    community: str | None,
    config: Config,
    model: str | None,
    page: int,
    published: bool,
    query: str | None,
    repository: str | None,
    size: int | None = None,
    sort: str | None = None,
) -> tuple[AsyncRecordsClient, dict]:
    """Prepare the search for records."""
    client = await get_async_client(repository, config=config)
    records_api: AsyncRecordsClient = client.records
    if model is not None:
        records_api = records_api.with_model(model)
    if published:
        records_api = records_api.published_records
    else:
        records_api = records_api.draft_records
    args: dict[str, str | RecordStatus] = {}
    if community:
        args["community"] = community
    if sort:
        args["sort"] = sort
    if query:
        args["q"] = query
    if page is not None:
        args["page"] = str(page)
    if size is not None:
        args["size"] = str(size)
    if published:
        args["status"] = RecordStatus.PUBLISHED
    else:
        args["status"] = RecordStatus.DRAFT
    return records_api, args
