#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""CLI commands for managing repositories."""

import sys
import urllib
import urllib.parse
from collections.abc import Generator
from functools import partial
from typing import Any

import rich_click as click
from rich import box
from rich.console import Console
from rich.table import Table
from yarl import URL

from nrp_cmd.async_client import AsyncRepositoryClient, get_async_client
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.config import Config
from nrp_cmd.config.repository import RepositoryConfig
from nrp_cmd.converter import converter

from .arguments import (
    Output,
    VerboseLevel,
    argument_with_help,
    with_config,
    with_output,
    with_verbosity,
)
from .base import OutputWriter


@argument_with_help("url", type=str, help="The URL of the repository")
@argument_with_help(
    "alias", type=str, required=False, help="The alias of the repository"
)
@click.option("--token", type=str, help="The token to access the repository")
@click.option(
    "--verify-tls/--no-verify-tls", default=True, help="Verify the TLS certificate"
)
@click.option("--retry-count", type=int, default=5, help="Number of retries")
@click.option(
    "--retry-after-seconds", type=int, default=5, help="Retry after this interval"
)
@click.option(
    "--anonymous/--no-anonymous",
    default=False,
    help="Do not store the token in the configuration",
)
@click.option(
    "--default/--no-default", default=False, help="Set this repository as the default"
)
@click.option(
    "--launch-browser/--no-launch-browser",
    default=True,
    help="Open the browser to create a token",
)
@with_config
@with_verbosity
@async_command
async def add_repository(
    *,
    config: Config,
    out: Output,
    url: str,
    alias: str | None,
    token: str | None,
    verify_tls: bool,
    retry_count: int,
    retry_after_seconds: int,
    anonymous: bool,
    default: bool,
    launch_browser: bool,
) -> None:
    """Add a new repository to the configuration."""
    console = Console()
    console.print()

    if not url.startswith("https://"):
        url = f"https://{url}"

    if alias is None:
        alias = urllib.parse.urlparse(url).netloc

    try:
        config.get_repository(alias)
        console.print(f'[red]Repository with alias "{alias}" already exists[/red]')
        sys.exit(1)
    except KeyError:
        pass

    console.print(
        f"Adding repository [green]{url}[/green] with alias [green]{alias}[/green]"
    )

    if token is None and not anonymous:
        # open  default browser with url to create token

        login_url = f"{url}/account/settings/applications/tokens/new"

        console.print(
            f"\nI will try to open the following url in your browser:\n{login_url}\n",
        )
        console.print(
            "Please log in inside the browser.\nWhen the browser tells you "
            "that the token has been created, \ncopy the token and paste it here.",
        )
        console.print("Press enter to open the page ...")
        click.getchar()

        if launch_browser:
            try:
                click.launch(login_url)
            except Exception:  # noqa
                console.print(
                    "Failed to open the browser. Please open the URL above manually."
                )

        # wait until the token is created at /account/settings/applications/tokens/retrieve
        token = click.prompt("\nPaste the token here").strip()

    console.print("Creating repository with token ...")
    config.add_repository(
        RepositoryConfig(
            alias=alias,
            url=URL(url),
            token=token,
            verify_tls=verify_tls,
            retry_count=retry_count,
            retry_after_seconds=retry_after_seconds,
        )
    )
    if default or len(config.repositories) == 1:
        config.set_default_repository(alias)

    # check if the repository is reachable and get its parameters
    client: AsyncRepositoryClient = await get_async_client(alias, config=config)
    await client.get_repository_info(refresh=True)

    console.print(f"[green]Added repository {alias} -> {url}[/green]")
    config.save()


@argument_with_help("alias", type=str, help="The alias of the repository")
@with_config
@async_command
async def remove_repository(*, config: Config, alias: str) -> None:
    """Remove a repository from the configuration."""
    console = Console()
    console.print()
    config.remove_repository(alias)
    console.print(f'[green]Removed repository "{alias}"[/green]')
    config.save()


@argument_with_help("alias", type=str, help="The alias of the repository")
@with_config
@async_command
async def select_repository(*, config: Config, alias: str) -> None:
    """Select a default repository."""
    console = Console()
    console.print()

    config.set_default_repository(alias)
    console.print(f'[green]Selected repository "{alias}"[/green]')
    config.save()


@argument_with_help("alias", type=str, help="The alias of the repository")
@with_config
@async_command
async def enable_repository(
    *,
    config: Config,
    alias: str,
) -> None:
    """Enable a disabled repository. Enabling it will make it usable for subsequent commands."""
    console = Console()
    console.print()

    for repo in config.repositories:
        if repo.alias == alias:
            repo.enabled = True
            break
    else:
        console.print(f'[red]Repository "{alias}" not found[/red]')
        sys.exit(1)
    console.print(f'[green]Enabled repository "{alias}"[/green]')
    config.save()


@argument_with_help("alias", type=str, help="The alias of the repository")
@with_config
@async_command
async def disable_repository(
    *,
    config: Config,
    alias: str,
) -> None:
    """Disable a repository. This repository will not be used for any operation."""
    console = Console()
    console.print()

    for repo in config.repositories:
        if repo.alias == alias:
            repo.enabled = False
            break
    else:
        console.print(f'[red]Repository "{alias}" not found[/red]')
        sys.exit(1)
    console.print(f'[green]Disabled repository "{alias}"[/green]')
    config.save()


@with_output
@with_verbosity
@with_config
@async_command
async def list_repositories(
    *,
    config: Config,
    out: Output,
) -> None:
    """List all repositories."""
    console = Console()

    with OutputWriter(
        out.output,
        out.output_format,
        console,
        partial(output_tables, verbose=out.verbosity == VerboseLevel.VERBOSE),
    ) as printer:
        printer.output(
            [
                dump_repo_configuration(
                    repo, out.verbosity == VerboseLevel.VERBOSE, config.default_alias
                )
                for repo in config.repositories
            ]
        )


@with_verbosity(VerboseLevel.VERBOSE)
@with_output
@with_config
@argument_with_help("alias", type=str, help="The alias of the repository")
@click.option(
    "--refresh",
    is_flag=True,
    help="Force a refresh of the information",
)
@async_command
async def describe_repository(
    *,
    config: Config,
    out: Output,
    alias: str,
    refresh: bool,
) -> None:
    """Get information about a repository."""
    console = Console()

    client: AsyncRepositoryClient = await get_async_client(alias, config=config)

    repo_config = config.get_repository(alias)

    if refresh:
        repo_config.info = await client.get_repository_info(refresh=refresh)
        config.save()

    with OutputWriter(
        out.output,
        out.output_format,
        console,
        output_repository_info_table,
    ) as printer:
        printer.output(
            dump_repo_configuration(
                repo_config,
                verbose=out.verbosity == VerboseLevel.VERBOSE,
                default_alias=config.default_alias,
            )
        )


def dump_repo_configuration(
    repo: RepositoryConfig, verbose: bool, default_alias: str | None
) -> dict[str, Any]:
    """Dump the repository configuration into a json-compatible structure."""
    if not verbose:
        return {
            "alias": repo.alias,
            "url": str(repo.url),
            "default": repo.alias == default_alias,
        }
    return {
        "alias": repo.alias,
        "url": str(repo.url),
        "token": "***" if repo.token else "anonymous",
        "verify_tls": repo.verify_tls,
        "retry_count": repo.retry_count,
        "retry_after_seconds": repo.retry_after_seconds,
        "info": converter.unstructure(repo.info, keep_nulls=True)
        if repo.info
        else None,
        "default": repo.alias == default_alias,
    }


def output_tables(
    data: Any, *, verbose: bool, **kwargs: Any
) -> Generator[Table, None, None]:
    """Output the information about the repositories formatted as a table."""
    if not verbose:
        table = Table(title="Repositories", box=box.SIMPLE, title_justify="left")
        table.add_column("Alias", style="cyan")
        table.add_column("URL")
        table.add_column("Default", style="green")

        for repo in data:
            table.add_row(
                repo["alias"],
                str(repo["url"]),
                "✓" if repo["default"] else "",
            )
        yield table
    else:
        for repo in data:
            yield from output_repository_info_table(repo, **kwargs)


def output_repository_info_table(
    data: dict[str, Any],
    **kwargs: Any,  # noqa: ANN401
) -> Generator[Table, None, None]:
    """Output the information about a repository formatted as a table."""
    repo = data
    table = Table(
        title=f"Repository '{repo["alias"]}'",
        box=box.SIMPLE,
        show_header=False,
        title_justify="left",
    )
    table.add_column("", style="cyan")
    table.add_column("")
    if repo["info"]:
        table.add_row("Name", repo["info"]["name"])
    table.add_row("URL", str(repo["url"]))
    table.add_row("Token", repo["token"])
    table.add_row("TLS Verify", "✓" if repo["verify_tls"] else "[red]skip[/red]")
    table.add_row("Retry Count", str(repo["retry_count"]))
    table.add_row("Retry After Seconds", str(repo["retry_after_seconds"]))
    table.add_row("Default", "✓" if repo["default"] else "")
    if repo["info"]:
        table.add_row("Version", repo["info"]["version"])
        table.add_row("Invenio Version", repo["info"]["invenio_version"])
        table.add_row("Transfers", ", ".join(sorted(repo["info"]["transfers"])))
        table.add_row("Records url", str(repo["info"]["links"]["records"]))
        table.add_row("User drafts", str(repo["info"]["links"]["drafts"]))
    yield table

    if repo["info"]:
        model_info: Any
        for model_name, model_info in repo["info"]["models"].items():
            table = Table(
                title=f"Model '{model_name}'",
                box=box.SIMPLE,
                show_header=False,
                title_justify="left",
            )
            table.add_column("", style="cyan")
            table.add_column("")
            table.add_row("Name", model_info["name"])
            table.add_row("Description", model_info["description"])
            table.add_row("Version", model_info["version"])
            table.add_row("Features", ", ".join(model_info["features"]))
            table.add_row("HTML", str(model_info["links"]["html"]))
            table.add_row("Model Schema", str(model_info["links"]["model"]))
            table.add_row("Published Records URL", str(model_info["links"]["records"]))
            table.add_row("User Records URL", str(model_info["links"]["drafts"]))

            for ct in sorted(
                model_info["content_types"], key=lambda x: x["content_type"]
            ):
                table.add_row("Content-Type", ct["content_type"])
                table.add_row("", ct["name"] + "\n" + ct["description"])
                table.add_row("    Schema", str(ct["schema"]))
                table.add_row("    Can Export", "✓" if ct["can_export"] else "")
                table.add_row("    Can Deposit", "✓" if ct["can_deposit"] else "")

            yield table
