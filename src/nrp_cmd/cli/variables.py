#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Commandline clients for working with variables."""


from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table

from nrp_cmd.config import Config

from .arguments import Output, argument_with_help, with_config, with_output
from .base import OutputWriter


@with_config
@argument_with_help("name", type=str, help="The name of the variable")
@argument_with_help("values", type=str, nargs=-1, help="The values of the variable")
def set_variable(*, config: Config, name: str, values: list[str]) -> None:
    """Add a variable to the configuration."""
    console = Console()
    console.print()
    variables = config.load_variables()

    variables[name] = values
    variables.save()
    msg = f"Added variable {name} -> "
    ln = len(msg)
    formatted_values = (f"\n{' ' * ln}".join(values)).strip()
    console.print(f"[green]{msg}{formatted_values}[/green]")


@with_config
@argument_with_help("name", type=str, help="The name of the variable")
def remove_variable(config: Config, name: str) -> None:
    """Remove a variable from the configuration."""
    console = Console()
    console.print()
    variables = config.load_variables()

    del variables[name]
    variables.save()

    console.print(f"[green]Removed variable {name}[/green]")


@with_config
@with_output
def list_variables(*, config: Config, out: Output) -> None:
    """List all variables."""
    console = Console()
    variables = config.load_variables()

    with OutputWriter(
        out.output, out.output_format, console, variables_table
    ) as printer:
        printer.output(variables.variables)


@with_config
@with_output
@argument_with_help("variable", type=str, help="The name of the variable")
def get_variable(*, config: Config, variable: str, out: Output) -> None:
    """Get all variables."""
    console = Console()
    variables = config.load_variables()
    value = variables.get(variable)

    def variable_table(data: list[str], **kwargs: Any) -> str:
        return "\n".join(data)

    with OutputWriter(
        out.output, out.output_format, console, variable_table
    ) as printer:
        printer.output(value)


def variables_table(data: dict[str, list[str]], **kwargs: Any) -> Table:
    """Render a table of variables."""
    table = Table(title="Variables", box=box.SIMPLE, title_justify="left")
    table.add_column("Name", style="cyan")
    table.add_column("Values")
    for name, values in data.items():
        table.add_row(name, "\n".join(values))
    return table
