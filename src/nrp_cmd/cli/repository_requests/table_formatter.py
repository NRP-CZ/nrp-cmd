#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Formatter for request and request types tables."""

from collections.abc import Generator
from typing import Any

from rich import box
from rich.table import Table

from nrp_cmd.cli.base import write_table_row
from nrp_cmd.converter import converter
from nrp_cmd.types.requests import Request, RequestType


def format_request_table(data: Request, **kwargs: Any) -> Generator[Table, None, None]:
    """Format request table both for requests and request types."""
    table = Table(
        title=f"Request {data.id}", box=box.SIMPLE, title_justify="left"
    )
    write_table_row(table, "status", data.status)
    write_table_row(table, "type", data.type)
    write_table_row(table, "created", data.created)
    write_table_row(table, "updated", data.updated)
    write_table_row(table, "topic", data.topic)
    write_table_row(table, "receiver", data.receiver)
    write_table_row(table, "sender", data.created_by)
    if data.payload:
        if data.payload.draft_record:
            write_table_row(table, "draft record", data.payload.draft_record.links.self_)
            write_table_row(table, "draft record html", data.payload.draft_record.links.self_html)
        if data.payload.published_record:
            write_table_row(table, "published record", data.payload.published_record.links.self_)
            write_table_row(table, "published record html", data.payload.published_record.links.self_html)
        if len(data.payload._extra_data or {}) > 0:
            write_table_row(table, "payload", data.payload._extra_data)
    write_table_row(table, "links", "")
    write_table_row(table, "    self", data.links.self_)
    write_table_row(table, "    self_html", data.links.self_html)
    write_table_row(table, "    comments", data.links.comments)
    write_table_row(table, "    timeline", data.links.timeline)
    write_table_row(table, "actions", "")
    for action_name, action_link in converter.unstructure(data.links.actions).items():
        write_table_row(table, f"    {action_name}", action_link)
    yield table


def format_request_type_table(data: RequestType) -> Generator[Table, None, None]:
    """Format request type table."""
    table = Table(
        title="Request Type",
        box=box.SIMPLE,
        title_justify="left",
        show_header=False,
    )
    write_table_row(table, "id", data.type_id)
    write_table_row(table, "actions", "")
    for action_name, action_link in converter.unstructure(data.links.actions).items():
        write_table_row(table, f"    {action_name}", action_link)
    yield table


def format_request_and_types_table(
    data: dict[str, Any], **kwargs: Any
) -> Generator[Table, None, None]:
    """Format request and request types table."""
    request: Request
    for request in converter.structure(data["requests"], list[Request]):
        yield from format_request_table(request)

    request_type: RequestType
    for request_type in converter.structure(data["request_types"], list[RequestType]):
        yield from format_request_type_table(request_type)
