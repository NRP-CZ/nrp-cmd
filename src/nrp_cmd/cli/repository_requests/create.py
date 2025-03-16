#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line interface for getting records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import rich_click as click
from rich.console import Console

from nrp_cmd.async_client import (
    AsyncRepositoryClient,
    limit_connections,
)
from nrp_cmd.async_client.connection import limit_connections
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.config import Config
from nrp_cmd.types.records import Record
from nrp_cmd.types.requests import Request

from ..arguments import (
    Model,
    Output,
    argument_with_help,
    with_config,
    with_model,
    with_output,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)
from .table_formatter import format_request_table

if TYPE_CHECKING:
    from nrp_cmd.types.requests import RequestType


@with_config
@with_repository
@with_resolved_vars("record_id")
@with_output
@with_model
@with_verbosity
@argument_with_help("request_type_id", type=str, help="Request type ID")
@argument_with_help("record_id", type=str, help="Record ID")
@argument_with_help("variable", type=str, required=False, help="Variable name")
@click.option("--submit/--no-submit", default=True, help="Submit the request")
@async_command
async def create_request(
    *,
    config: Config,
    repository: Optional[str] = None,
    request_type_id: str,
    record_id: str,
    variable: Optional[str] = None,
    out: Output,
    model: Model,
    submit: bool = True,
) -> None:
    """Create a request."""
    console = Console()

    with limit_connections(10):
        (
            record,
            _final_record_id,
            _repository_config,
            _record_client,
            repository_client,
        ) = await read_record(
            record_id,
            repository,
            config,
            False,
            model.model,
            model.published,
            model.draft,
        )
        request = await create_request_helper(
            console, repository_client, record, request_type_id, submit
        )

    with OutputWriter(
        out.output, out.output_format, console, format_request_table
    ) as printer:
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
        raise click.Abort()

    return await repository_client.requests.create(request_type, {}, submit=submit)
