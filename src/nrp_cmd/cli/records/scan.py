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

from rich.console import Console

from nrp_cmd.async_client.base_client import RecordStatus
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.base import set_variable as setvar
from nrp_cmd.cli.records.table_formatters import (
    format_record_table,
)
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
from .search import prepare_records_api


@with_config
@with_repository
@with_output
@with_verbosity
@with_setvar
@with_model(community=True)
@argument_with_help("query", type=str, required=False, help="Query string")
@async_command
async def scan_records(
    *,
    config: Config,
    repository: Optional[str],
    query: Optional[str] = None,
    variable: Optional[str] = None,
    model: Model,
    out: Output,
) -> None:
    """Return all records inside repository that match the given query."""
    console = Console()

    records_api = await prepare_records_api(
        config, model.model, model.draft, model.published, repository
    )

    urls: set[str] = set()

    with OutputWriter(
        out.output,
        out.output_format,
        console,
        partial(format_record_table, verbosity=out.verbosity),  # type: ignore # mypy does not understand this
    ) as printer:
        printer.multiple()

        async with records_api.scan(
            q=query,
            model=model.model,
            status=RecordStatus.PUBLISHED if model.published else RecordStatus.DRAFT,
            facets={},
        ) as scan:
            async for entry in scan:
                link = str(entry.links.self_)
                if link not in urls:
                    printer.output(entry)
                    urls.add(link)

    if variable:
        setvar(config, variable, list(urls))
