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

from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.base import set_variable as setvar
from nrp_cmd.cli.records.table_formatters import (
    format_record_table,
)
from nrp_cmd.config import Config

from ..arguments import (
    Output,
    with_config,
    with_output,
    with_repository,
    with_setvar,
    with_verbosity,
)
from .search import _prepare_search


@async_command
@with_config
@with_repository
@with_output
@with_verbosity
@with_setvar
async def scan_records(
    # generic options
    *,
    config: Config,
    repository: Optional[str],
    # specific options
    query: Annotated[Optional[str], typer.Argument(help="Query string")] = None,
    variable: Optional[str] = None,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    community: Annotated[Optional[str], typer.Option(help="Community name")] = None,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    out: Output,
) -> None:
    """Return all records inside repository that match the given query."""
    console = Console()

    records_api, args = await _prepare_search(
        community,
        config,
        model,
        1,
        published,
        query,
        repository,
    )

    urls = set()
    last_created = None

    with OutputWriter(
        out.output,
        out.output_format,
        console,
        partial(format_record_table, verbosity=out.verbosity),  # type: ignore # mypy does not understand this
    ) as printer:
        printer.multiple()

        async with records_api.scan(**args) as scan:
            async for entry in scan:
                link = str(entry.links.self_)
                if link not in urls:
                    printer.output(entry)
                    urls.add(link)

    if variable:
        setvar(config, variable, list(urls))
