#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line interface for accepting requests."""

from __future__ import annotations

from typing import Optional

from rich.console import Console

from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.config import Config

from ..arguments import (
    Output,
    argument_with_help,
    with_config,
    with_output,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)
from .table_formatter import format_request_table
from .utils import resolve_request


@with_config
@with_repository
@with_resolved_vars("request_id")
@argument_with_help("request_id", type=str, help="Request IDs")
@with_output
@with_verbosity
@async_command
async def accept_request(
    *, config: Config, repository: Optional[str] = None, request_id: str, out: Output
) -> None:
    """Accept a request."""
    console = Console()

    requests_client, request_url = await resolve_request(request_id, config, repository)

    request = await requests_client.accept(request_url)

    with OutputWriter(
        out.output, out.output_format, console, format_request_table
    ) as printer:
        printer.output(request)
