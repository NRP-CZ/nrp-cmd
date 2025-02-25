#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command-line interface for downloading records."""

from asyncio import TaskGroup
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client import limit_connections
from nrp_cmd.async_client.streams import FileSink
from nrp_cmd.cli.base import OutputFormat, async_command
from nrp_cmd.cli.records.get import get_single_record
from nrp_cmd.config import Config
from nrp_cmd.progress import show_progress

from ..arguments import (
    Output,
    VerboseLevel,
    with_config,
    with_output,
    with_progress,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)


@async_command
@with_output
@with_config
@with_repository
@with_resolved_vars("record_ids")
@with_verbosity
@with_progress
async def download_record(
    # generic options
    *,
    config: Config,
    repository: Optional[str],
    # specific options
    record_ids: Annotated[list[str], typer.Argument(help="Record ID")],
    out: Output,
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    expand: Annotated[bool, typer.Option(help="Expand the record")] = False,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
) -> None:
    """Download a record from the repository.

    The metadata of the record are stored together with the files in output directory.
    """
    console = Console()
    tasks = []
    with (
        limit_connections(10),
        show_progress(total=len(record_ids), quiet=not out.progress),
    ):
        async with TaskGroup() as tg:
            for record_id in record_ids:
                tasks.append(
                    tg.create_task(
                        download_single_record(
                            record_id,
                            console,
                            config,
                            repository,
                            model,
                            out.output,
                            out.output_format,
                            published,
                            draft,
                            expand,
                            out.verbosity,
                        )
                    )
                )
    abort = False
    for task in tasks:
        if task.result() is False:
            abort = True

    if abort:
        console.print("[red]Failed to download some of the records[/red]")
        raise typer.Abort()

async def download_single_record(
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
) -> bool:
    """Download record with the given id together with its files."""
    # 1. download record metadata
    if not output:
        output = Path("{id}")

    if not output_format:
        output_format = OutputFormat.JSON

    record, output, repository_config, repository_client = await get_single_record(
        record_id,
        console,
        config,
        repository,
        model,
        output / "metadata{ext}",
        output_format,
        published,
        draft,
        expand,
        verbosity=VerboseLevel.NORMAL,
    )

    if not record:
        return False

    output_dir = output.parent if output and output.parent else Path.cwd()

    assert repository_client
    file_client = repository_client.files

    file_list = await file_client.list(record)

    tasks = []
    async with TaskGroup() as tg:
        for file_ in file_list:
            file_key = file_.key
            # sanitize the key
            if "/" in file_key:
                file_key = file_key.replace("/", "_")
            file_key = file_key.replace(":", "_")
            file_key = file_key.replace("..", "_")
            tasks.append(
                tg.create_task(
                    file_client.download(
                        file_, FileSink(output_dir / file_key), progress=file_.key
                    )
                )
            )

    ok = True
    for idx, task in enumerate(tasks):
        if task.exception():
            ok = False
            console.print(
                f"[red]Failed to download file {file_list[idx].key} of {record_id}[/red]"
            )

    if ok and verbosity != VerboseLevel.QUIET:
        console.print(f"[green]Record {record_id} downloaded to {output_dir}[/green]")
    return ok
