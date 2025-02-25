#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline client for downloading files."""
# TODO: test !!!!
import sys
from asyncio import TaskGroup
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from nrp_cmd.async_client.streams import FileSink
from nrp_cmd.cli.base import OutputFormat, async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.cli.records.record_file_name import create_output_file_name
from nrp_cmd.config import Config
from nrp_cmd.converter import converter
from nrp_cmd.progress import show_progress

from ..arguments import (
    Output,
    VerboseLevel,
    with_config,
    with_progress,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)


@async_command
@with_config
@with_repository
@with_resolved_vars("record_id")
@with_verbosity
@with_progress
async def download_files(
    *,
    # generic options
    config: Config,
    repository: Optional[str] = None,
    # specific options
    record_id: Annotated[str, typer.Argument(help="Record ID")],
    keys: Annotated[list[str], typer.Argument(help="File key")],
    output: Annotated[Optional[Path], typer.Option("-o", help="Output path")],
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
    out: Output,
) -> None:
    """Download files from a record."""
    output = output or Path.cwd()
    console = Console()

    with show_progress(total=1, quiet=not out.progress):
        await download_single_record_files(
            console,
            record_id,
            keys,
            output,
            config,
            repository,
            model,
            published,
            draft,
            verbosity=out.verbosity,
        )


async def download_single_record_files(
    console,
    record_id,
    keys,
    output,
    config,
    repository,
    model,
    published,
    draft,
    verbosity,
):
    (
        record,
        record_id,
        repository_config,
        record_client,
        repository_client,
    ) = await read_record(record_id, repository, config, False, model, published, draft)
    assert repository_client
    file_client = repository_client.files

    files = await file_client.list(record)

    if "*" in keys:
        keys = [file.key for file in files]
    else:
        allowed_keys = {file.key for file in files}
        if set(keys) - allowed_keys:
            console.print(
                f"[red]Some keys not found in the record: {set(keys) - allowed_keys}[/red]"
            )
            return False

    tasks = []
    async with TaskGroup() as tg:
        for key in keys:
            try:
                file_ = next(f for f in files if f.key == key)
            except KeyError:
                print(f"Key {key} not found in files, skipping ...", file=sys.stderr)
                continue

            is_file = "{key}" in str(output)

            # sanitize the key
            if "/" in key:
                key = key.replace("/", "_")
            if ":" in key:
                key = key.replace(":", "_")

            file_output = create_output_file_name(
                output,
                key,
                file_,
                OutputFormat.JSON,
                record=converter.unstructure(record),  # type: ignore
            )

            if not is_file:
                file_output = file_output / key

            if file_output and file_output.parent:
                file_output.parent.mkdir(parents=True, exist_ok=True)

            tasks.append((
                key,
                file_output,
                tg.create_task(
                    file_client.download(
                        file_, FileSink(file_output), progress=file_.key
                    )
                ),
            ))

    ok = True
    for idx, (key, fname, task) in enumerate(tasks):
        if task.exception():
            ok = False
            console.print(f"[red]Failed to download file {key} of {record_id}[/red]")
        else:
            if verbosity != VerboseLevel.QUIET:
                console.print(
                    f"[green]File {key} of {record_id} downloaded to {fname}[/green]"
                )
    return ok
