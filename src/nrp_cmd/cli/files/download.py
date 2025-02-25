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
from pathlib import Path
from typing import Annotated, Optional

import typer

from nrp_cmd.async_client.streams import FileSink
from nrp_cmd.cli.base import OutputFormat, async_command
from nrp_cmd.cli.records.get import read_record
from nrp_cmd.cli.records.record_file_name import create_output_file_name
from nrp_cmd.config import Config

from ..arguments import with_config, with_repository, with_resolved_vars


@async_command
@with_config
@with_repository
@with_resolved_vars("record_id")
async def download_files(
    *,
    # generic options
    config: Config,
    repository: Optional[str] = None,
    # specific options
    record_id: Annotated[list[str], typer.Argument(help="Record ID(s)")],
    keys: Annotated[list[str], typer.Argument(help="File key")],
    output: Annotated[Optional[Path], typer.Option("-o", help="Output path")],
    model: Annotated[Optional[str], typer.Option(help="Model name")] = None,
    published: Annotated[
        bool, typer.Option("--published/", help="Include only published records")
    ] = False,
    draft: Annotated[
        bool, typer.Option("--draft/", help="Include only drafts")
    ] = False,
) -> None:
    """Download files from a record."""
    output = output or Path.cwd()

    async with Downloader() as downloader:
        for record_id in ids:
            (
                record,
                record_id,
                repository_config,
                record_client,
                repository_client,
            ) = await read_record(
                record_id, repository, config, limiter, False, model, published, draft
            )
            files = await record.files().list()

            # TODO: better way of handling tls verification
            if not repository_config.verify_tls:
                downloader.verify_tls = False

            if "*" in keys:
                keys = [file.key for file in files.entries]
            else:
                keys = list(set(keys) & {file.key for file in files.entries})

            for key in keys:
                try:
                    file = files[key]
                except KeyError:
                    print(
                        f"Key {key} not found in files, skipping ...", file=sys.stderr
                    )
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
                    file,
                    OutputFormat.JSON,
                    record=record.model_dump(mode="json"),  # type: ignore
                )

                if not is_file:
                    file_output = file_output / key

                if file_output and file_output.parent:
                    file_output.parent.mkdir(parents=True, exist_ok=True)

                downloader.add(str(file.links.content), FileSink(file_output))
