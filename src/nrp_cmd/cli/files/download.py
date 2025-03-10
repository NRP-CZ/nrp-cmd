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
from asyncio import Task, TaskGroup
from pathlib import Path
from typing import Any, Optional

import rich_click as click
from rich.console import Console

from nrp_cmd.async_client.streams import FileSink
from nrp_cmd.cli.base import OutputFormat, async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.cli.records.record_file_name import create_output_file_name
from nrp_cmd.config import Config
from nrp_cmd.converter import converter
from nrp_cmd.progress import show_progress

from ..arguments import (
    Model,
    Output,
    VerboseLevel,
    argument_with_help,
    with_config,
    with_model,
    with_output,
    with_progress,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)


@with_config
@with_repository
@with_resolved_vars("record_id")
@with_output
@with_progress
@with_verbosity
@with_model
@argument_with_help("record_id", type=str, help="Record ID")
@argument_with_help("keys", type=str, nargs=-1, help="File key")
@click.option("-o", "--output", type=click.Path(), help="Output path")
@async_command
async def download_files(
    *,
    config: Config,
    repository: Optional[str] = None,
    record_id: str,
    keys: list[str],
    output: Optional[Path] = None,
    model: Model,
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
            model.model,
            model.published,
            model.draft,
            verbosity=out.verbosity,
        )


async def download_single_record_files(
    console: Console,
    record_id: str,
    keys: list[str],
    output: Path,
    config: Config,
    repository: str | None,
    model: str | None,
    published: bool,
    draft: bool,
    verbosity: VerboseLevel,
):
    (
        record,
        record_id_url,
        _repository_config,
        _record_client,
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

    tasks: list[tuple[str, Any, Task[Any]]] = []
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
    for key, fname, task in tasks:
        if task.exception():
            ok = False
            console.print(
                f"[red]Failed to download file {key} of {record_id_url}[/red]"
            )
        else:
            if verbosity != VerboseLevel.QUIET:
                console.print(
                    f"[green]File {key} of {record_id_url} downloaded to {fname}[/green]"
                )
    return ok
