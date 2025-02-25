#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line interface for getting records."""

from __future__ import annotations

from pathlib import Path  # noqa
from typing import TYPE_CHECKING, Annotated, Optional

import typer  # noqa
from rich.console import Console

from nrp_cmd.async_client import (
    AsyncRepositoryClient,
    limit_connections,
)
from nrp_cmd.async_client.connection import limit_connections
from nrp_cmd.cli.base import OutputFormat, OutputWriter, async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.config import Config
from nrp_cmd.types.records import Record
from nrp_cmd.types.requests import Request

from ..arguments import with_config, with_repository, with_resolved_vars
from .table_formatter import format_request_table

if TYPE_CHECKING:
    from nrp_cmd.types.requests import RequestType


@async_command
@with_config
@with_repository
@with_resolved_vars("record_id")
async def create_request(
    *,
    # generic arguments
    config: Config,
    repository: Optional[str] = None,
    # specific arguments
    request_type_id: Annotated[str, typer.Argument(help="Request type ID")],
    record_id: Annotated[str, typer.Argument(help="Record ID")],
    variable: Annotated[Optional[str], typer.Argument(help="Variable name")] = None,
    output: Annotated[
        Optional[Path], typer.Option("-o", help="Save the output to a file")
    ] = None,
    output_format: Annotated[
        Optional[OutputFormat],
        typer.Option("-f", help="The format of the output"),
    ] = None,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = True,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
    submit: Annotated[
        bool, typer.Option("--submit/--no-submit", help="Submit the request")
    ] = True,
) -> None:
    """Create a request."""
    console = Console()

    with limit_connections(10):
        (
            record,
            final_record_id,
            repository_config,
            record_client,
            repository_client,
        ) = await read_record(
            record_id, repository, config, False, model, published, draft
        )
        request = await create_request_helper(
            console, repository_client, record, request_type_id, submit
        )

    with OutputWriter(output, output_format, console, format_request_table) as printer:
        printer.output(request)

    if variable:
        variables = config.load_variables()
        variables[variable[1:]] = [str(request.links.self_)]
        variables.save()


async def create_request_helper(
    console: Console,
    repository_client: AsyncRepositoryClient,
    record: Record,
    request_type_id: str,
    submit: bool,
) -> Request:
    request_types = await repository_client.requests.applicable_requests(record)

    request_type: RequestType | None = next(
        (rt for rt in request_types.hits if rt.type_id == request_type_id), None
    )
    if not request_type:
        console.print(
            f"[red]Request type {request_type_id} not applicable to record {record.id}[/red]"
        )
        raise typer.Abort()

    return await repository_client.requests.create(request_type, {}, submit=submit)
