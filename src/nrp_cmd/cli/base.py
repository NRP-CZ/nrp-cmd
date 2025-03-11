#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Base utilities for the commandline client."""

import functools
import inspect
import json
from collections.abc import Callable, Generator, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Protocol, Self, get_origin

import yaml
from rich.console import Console
from rich.table import Table

from nrp_cmd.config import Config
from nrp_cmd.converter import converter

from .arguments import OutputFormat

if TYPE_CHECKING:
    from io import TextIOWrapper


def format_output(output_format: OutputFormat, data: Any) -> str:  # noqa: ANN401
    """Format the output according to the given format.

    Only the json, jsonl and yaml formats are supported.
    """
    if not isinstance(data, (dict, list)):
        data = converter.unstructure(data)
    if isinstance(data, list):
        unstructured_data = []
        for record in data:
            if not isinstance(record, (dict, list)):
                unstructured_data.append(converter.unstructure(record))
            else:
                unstructured_data.append(record)
        data = unstructured_data
    match output_format:
        case OutputFormat.JSON:
            return json.dumps(data, indent=4)
        case OutputFormat.JSON_LINES:
            return json.dumps(
                data, ensure_ascii=False, separators=(",", ":"), indent=None
            ).replace("\n", "\\n")
        case OutputFormat.YAML:
            return yaml.safe_dump(data)
        case _:
            raise ValueError(f"Unknown output format: {output_format}")


def format_table_value(value: list | dict | Any) -> str:  # noqa: ANN401
    """Format a value (dist, list or primitive) for a table."""
    if isinstance(value, list):
        if all(isinstance(x, dict) for x in value):
            return ",\n".join(
                json.dumps(x, indent=2, ensure_ascii=False) for x in value
            )
        return ", ".join(str(x) for x in value)
    if isinstance(value, dict):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return str(value)


def write_table_row(table: Table, k: str, v: Any, prefix: str = "") -> None:  # noqa: ANN401
    """Write a row into a table."""
    if isinstance(v, dict):
        table.add_row(prefix + k, "")
        for k1, v1 in v.items():
            table.add_row(prefix + "    " + k1, format_table_value(v1))
    else:
        table.add_row(prefix + k, format_table_value(v))


def _is_typer_argument(name: str, parameter: inspect.Parameter) -> bool:
    """Check if the annotation contains typer argument / option."""
    annotation = parameter.annotation
    if get_origin(annotation) is not Annotated:
        return False

    for md in annotation.__metadata__:
        if isinstance(md, (typer.models.ArgumentInfo, typer.models.OptionInfo)):
            return True
    return False


def async_command(func: Any) -> Callable[..., None]:
    """Run an async function synchronously.

    This decorator is used to run an async function synchronously.
    """
    import asyncio

    import uvloop

    @functools.wraps(func)
    def runner(*args: Any, **kwargs: Any):
        with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
            runner.run(func(*args, **kwargs))

    return runner


def set_variable(config: Config, name: str, value: list[str] | str) -> None:
    """Set a variable into the configuration (local directory or global)."""
    if not isinstance(value, list):
        value = [value]

    variables = config.load_variables()

    if name.startswith("@"):
        name = name[1:]
    if name.startswith("+"):
        name = name[1:]
        variables[name] = variables.get(name, []) + value  # type: ignore
    else:
        variables[name] = value
    variables.save()


class TableMaker(Protocol):
    """A function that converts data into a table or a list of tables."""

    def __call__(
        self, data: Any, **kwargs: Any
    ) -> (
        Table
        | Generator[Table, None, None]
        | list[Table]
        | str
        | Generator[str, None, None]
    ):
        """Create a table or a list of tables from the data."""
        ...


class OutputWriter:
    """A Writer capable of writing output to a file or console and formatting it to table, json or yaml."""

    def __init__(
        self,
        output_file: Path | None,
        output_format: OutputFormat | None,
        console: Console,
        table_maker: TableMaker,
    ) -> None:
        """Initialize the output writer."""
        self.output_file = output_file
        self.output_format = output_format
        self.console = console
        self.table_maker = table_maker
        self._stream: TextIOWrapper | None = None
        self._multiple = False
        self._output_encountered = False

    def __enter__(self) -> "Self":
        """Enter the context manager, opening the output file if provided."""
        if self.output_file:
            self._stream = self.output_file.open("w")
        else:
            self._stream = self.console
        return self

    def __exit__(self, exc_type, exc_value, traceback):  # noqa
        if self._multiple and self.output_format == OutputFormat.JSON:
            self._print("]")
        if self.output_file and self._stream:
            self._stream.close()
            self._stream = None

    def output(self, data: Any) -> None:  # noqa: ANN401
        """Output the data.

        If the output_format is 'table', the data will be passed to the table_maker function
        and printed as a table. Otherwise, the data will be formatted according to the output_format
        and printed.
        """
        assert (
            self._stream is not None
        ), "Output stream is not initialized, please use the context manager."

        if self._multiple and self._output_encountered:
            match self.output_format:
                case OutputFormat.JSON:
                    self._print(",")
                case OutputFormat.JSON_LINES:
                    self._print()
                case OutputFormat.YAML:
                    self._print("\n---")
                case _:
                    pass

        if self.output_format == OutputFormat.TABLE or self.output_format is None:
            if not isinstance(self._stream, Console):
                console = Console(file=self._stream)
            else:
                console = self._stream

            tables: Iterable[Table]
            if inspect.isgeneratorfunction(self.table_maker):
                tables = list(self.table_maker(data))
            else:
                generated_tables: Table | list[Table] = self.table_maker(data=data)  # type: ignore
                if not isinstance(generated_tables, (tuple, list)):
                    tables = [generated_tables]
                else:
                    tables = generated_tables

            for table in tables:
                console.print(table)
        else:
            data = format_output(self.output_format, data)
            self._print(data, end="" if self._multiple else "\n")
        self._output_encountered = True

    def multiple(self) -> None:
        """Set the output to be multiple records."""
        self._multiple = True
        if self.output_format == OutputFormat.JSON:
            assert (
                self._stream is not None
            ), "Output stream is not initialized, please use the context manager."
            self._print("[")

    def _print(self, data: Any = None, end: str = "\n") -> None:  # noqa: ANN401
        """Print the data to the output stream."""
        assert (
            self._stream is not None
        ), "Output stream is not initialized, please use the context manager."
        if hasattr(self._stream, "print"):
            self._stream.print(data, end=end)
        else:
            if data is not None:
                self._stream.write(str(data))
            self._stream.write(end)
