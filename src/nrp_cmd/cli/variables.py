#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline clients for working with variables."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from nrp_cmd.config import Config

from .base import OutputFormat, OutputWriter


def set_variable(
    name: Annotated[str, typer.Argument(help="The name of the variable")],
    values: Annotated[list[str], typer.Argument(help="The values of the variable")],
) -> None:
    """Add a variable to the configuration."""
    console = Console()
    console.print()
    config = Config.from_file()
    variables = config.load_variables()

    variables[name] = values
    variables.save()

    console.print(f"[green]Added variable {name} -> {values}[/green]")


def remove_variable(
    name: Annotated[str, typer.Argument(help="The name of the variable")],
) -> None:
    """Remove a variable from the configuration."""
    console = Console()
    console.print()
    config = Config.from_file()
    variables = config.load_variables()

    del variables[name]
    variables.save()

    console.print(f"[green]Removed variable {name}[/green]")


def list_variables(
    output: Annotated[
        Optional[Path],
        typer.Option(help="Save the output to a file"),
    ] = None,
    output_format: Annotated[
        Optional[OutputFormat],
        typer.Option(help="The format of the output"),
    ] = "table",    # type: ignore # typer needs it as a string and converts it to OutputFormat
) -> None:
    """List all variables."""
    console = Console()
    config = Config.from_file()
    variables = config.load_variables()

    with OutputWriter(output, output_format, console, variables_table) as printer:
        printer.output(variables.variables)


def get_variable(
    variable: Annotated[str, typer.Argument(help="The name of the variable")],
    output: Annotated[
        Optional[Path],
        typer.Option(help="Save the output to a file"),
    ] = None,
    output_format: Annotated[
        Optional[OutputFormat],
        typer.Option(help="The format of the output"),
    ] = "table",    # type: ignore # typer needs it as a string and converts it to OutputFormat
) -> None:
    """Get all variables."""
    console = Console()
    config = Config.from_file()
    variables = config.load_variables()
    value = variables.get(variable)

    def variable_table(data: list[str]) -> str:
        return "\n".join(data)

    with OutputWriter(output, output_format, console, variable_table) as printer:
        printer.output(value)


def variables_table(data: dict[str, list[str]]) -> Table:
    """Render a table of variables."""
    table = Table(title="Variables", box=box.SIMPLE, title_justify="left")
    table.add_column("Name", style="cyan")
    table.add_column("Values")
    for name, values in data.items():
        table.add_row(name, "\n".join(values))
    return table
