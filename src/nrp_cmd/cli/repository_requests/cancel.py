#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line interface for accepting requests."""

from __future__ import annotations

from pathlib import Path  # noqa
from typing import Annotated, Optional

import typer  # noqa
from rich.console import Console

from nrp_cmd.cli.base import OutputFormat, OutputWriter, async_command
from nrp_cmd.config import Config

from ..arguments import with_config, with_repository, with_resolved_vars
from .table_formatter import format_request_table
from .utils import resolve_request


@async_command
@with_config
@with_repository
@with_resolved_vars("request_id")
async def cancel_request(
    *,
    # generic arguments
    config: Config,
    repository: Optional[str] = None,
    # specific arguments
    request_id: Annotated[str, typer.Argument(help="Request IDs")],
    output: Annotated[
        Optional[Path], typer.Option("-o", help="Save the output to a file")
    ] = None,
    output_format: Annotated[
        Optional[OutputFormat],
        typer.Option("-f", help="The format of the output"),
    ] = None,
) -> None:
    """Cancel a request."""
    console = Console()
    requests_client, request_url = await resolve_request(request_id, config, repository)

    request = await requests_client.cancel(request_url)

    with OutputWriter(output, output_format, console, format_request_table) as printer:
        printer.output(request)
