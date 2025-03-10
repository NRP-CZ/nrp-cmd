#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command-line interface for searching records."""

from functools import partial
from typing import Optional

import rich_click as click
from rich.console import Console

from nrp_cmd.async_client import AsyncRecordsClient, RecordStatus, get_async_client
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.base import set_variable as setvar
from nrp_cmd.config import Config

from ..arguments import (
    Model,
    Output,
    argument_with_help,
    with_config,
    with_model,
    with_output,
    with_repository,
    with_setvar,
    with_verbosity,
)
from .table_formatters import (
    format_search_table,
)


@argument_with_help("query", type=str, required=False, help="Query string")
@click.option(
    "--size", type=int, default=10, help="Number of results to return on a page"
)
@click.option("--page", type=int, default=1, help="Page number")
@click.option("--sort", type=str, default="bestmatch", help="Sort order")
@with_config
@with_repository
@with_output
@with_verbosity
@with_setvar
@with_model(community=True)
@async_command
async def search_records(
    *,
    config: Config,
    repository: Optional[str] = None,
    query: Optional[str] = None,
    variable: Optional[str] = None,
    model: Model,
    size: int = 10,
    page: int = 1,
    sort: str = "bestmatch",
    out: Output,
) -> None:
    """Return a page of records inside repository that match the given query."""
    console = Console()

    records_api = await prepare_records_api(
        config, model.model, model.draft, model.published, repository
    )

    record_list = await records_api.search(
        q=query,
        page=page,
        size=size,
        sort=sort,
        model=model.model,
        status=RecordStatus.PUBLISHED if model.published else RecordStatus.DRAFT,
        facets={},
    )

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


async def prepare_records_api(
    config: Config,
    model: str | None,
    draft: bool,
    published: bool,
    repository: str | None,
) -> AsyncRecordsClient:
    """Get records API for the model and publish status."""
    client = await get_async_client(repository, config=config)
    records_api: AsyncRecordsClient = client.records
    if model is not None:
        records_api = records_api.with_model(model)
    # TODO: published AND draft should be allowed and use the new /all/ endpoint
    if published or not draft:
        records_api = records_api.published_records
    if draft:
        records_api = records_api.draft_records
    return records_api
