#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Main commandline client."""

from __future__ import annotations

import dataclasses
import logging
import logging.handlers
from collections.abc import Callable
from typing import Any, Optional

import rich_click as click
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich_click.rich_help_formatter import RichHelpFormatter

from nrp_cmd.cli.arguments import Argument, ClickCommand, with_errors
from nrp_cmd.cli.files import (
    delete_file,
    download_files,
    list_files,
    update_file_metadata,
    upload_files,
)
from nrp_cmd.cli.records import (
    create_record,
    delete_record,
    download_record,
    edit_record,
    get_record,
    publish_record,
    retract_record,
    scan_records,
    search_records,
    update_record,
    version_record,
)
from nrp_cmd.cli.repositories import (
    add_repository,
    describe_repository,
    disable_repository,
    enable_repository,
    list_repositories,
    remove_repository,
    select_repository,
)
from nrp_cmd.cli.repository_requests import (
    accept_request,
    cancel_request,
    create_request,
    decline_request,
    list_requests,
    submit_request,
)
from nrp_cmd.cli.variables import (
    get_variable,
    list_variables,
    remove_variable,
    set_variable,
)

logging.basicConfig(level=logging.ERROR)

commands: list[tuple[str, str, ClickCommand]] = [
    #
    #
    # verb centric
    #
    #
    ("add", "repository", add_repository),
    ("accept", "request", accept_request),
    ("cancel", "request", cancel_request),
    ("create", "record", create_record),
    ("create", "request", create_request),
    ("decline", "request", decline_request),
    ("delete", "file", delete_file),
    ("delete", "record", delete_record),
    ("describe", "repository", describe_repository),
    ("disable", "repository", disable_repository),
    ("download", "record", download_record),
    ("download", "files", download_files),
    ("download", "file", download_files),
    ("enable", "repository", enable_repository),
    ("get", "record", get_record),
    ("get", "variable", get_variable),
    ("list", "files", list_files),
    ("list", "records", search_records),
    ("list", "repositories", list_repositories),
    ("list", "requests", list_requests),
    ("list", "variables", list_variables),
    ("publish", "record", publish_record),
    ("retract", "record", retract_record),
    ("edit", "record", edit_record),
    ("version", "record", version_record),
    ("remove", "repository", remove_repository),
    ("remove", "variable", remove_variable),
    ("scan", "records", scan_records),
    ("search", "records", search_records),
    ("select", "repository", select_repository),
    ("set", "variable", set_variable),
    ("submit", "request", submit_request),
    ("upload", "file", upload_files),
    ("update", "record", update_record),
    ("update", "file", update_file_metadata),
    #
    #
    # noun centric
    #
    #
    ("files", "list", list_files),
    ("files", "delete", delete_file),
    ("files", "download", download_files),
    ("files", "upload", upload_files),
    ("files", "update", update_file_metadata),
    ("records", "create", create_record),
    ("records", "delete", delete_record),
    ("records", "download", download_record),
    ("records", "get", get_record),
    ("records", "list", search_records),
    ("records", "search", search_records),
    ("records", "scan", scan_records),
    ("records", "update", update_record),
    ("records", "edit", edit_record),
    ("records", "version", version_record),
    ("records", "publish", publish_record),
    ("records", "retract", retract_record),
    ("requests", "accept", accept_request),
    ("requests", "cancel", cancel_request),
    ("requests", "create", create_request),
    ("requests", "decline", decline_request),
    ("requests", "list", list_requests),
    ("requests", "submit", submit_request),
    ("repositories", "add", add_repository),
    ("repositories", "describe", describe_repository),
    ("repositories", "disable", disable_repository),
    ("repositories", "enable", enable_repository),
    ("repositories", "remove", remove_repository),
    ("repositories", "select", select_repository),
    ("repositories", "list", list_repositories),
    ("variables", "get", get_variable),
    ("variables", "set", set_variable),
    ("variables", "remove", remove_variable),
    ("variables", "list", list_variables),
]
"""CLI commands."""

click.rich_click.OPTION_GROUPS = {
    "nrp-cmd *": [
        {
            "name": "Output",
            "options": ["--verbose", "--quiet", "--output", "--output-format"],
        },
        {
            "name": "Configuration",
            "options": ["--config-path", "--repository"],
        },
        {
            "name": "Model",
            "options": [
                "--model",
                "--community",
                "--workflow",
                "--draft",
                "--published",
            ],
        },
        {
            "name": "Search",
            "options": ["--page", "--size", "--sort"],
        },
        {
            "name": "Variables",
            "options": ["--set"],
        },
        {
            "name": "Debugging and Logging",
            "options": [
                "--progress",
                "--log-url",
                "--log-request",
                "--log-response",
                "--log-stacktrace",
            ],
        },
    ],
}


class CommandWithAttributeHelp(click.RichCommand):
    def format_help(
        self, ctx: click.RichContext, formatter: RichHelpFormatter  # type: ignore[override]
    ) -> None:
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_arguments(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_arguments(
        self, ctx: click.RichContext, formatter: RichHelpFormatter
    ) -> None:
        """Writes all the options into the formatter if they exist."""
        options_rows: list[tuple[str, str]] = []
        for param in self.get_params(ctx):
            if isinstance(param, Argument):
                rv = param.get_argument_help_record(ctx)
                if rv is not None:
                    options_rows.append(rv)

        if len(options_rows) > 0:
            t_styles: dict[str, Any] = {
                "show_lines": formatter.config.style_options_table_show_lines,
                "leading": formatter.config.style_options_table_leading,
                "box": formatter.config.style_options_table_box,
                "border_style": formatter.config.style_options_table_border_style,
                "row_styles": formatter.config.style_options_table_row_styles,
                "pad_edge": formatter.config.style_options_table_pad_edge,
                "padding": formatter.config.style_options_table_padding,
            }
            if isinstance(formatter.config.style_options_table_box, str):
                t_styles["box"] = getattr(box, t_styles.pop("box"), None)  # type: ignore[arg-type]

            options_table = Table(
                highlight=True,
                show_header=False,
                expand=True,
                **t_styles,  # type: ignore[arg-type]
            )
            # Strip the required column if none are required
            for row in options_rows:
                options_table.add_row(*row)

            kw: dict[str, Any] = {
                "border_style": formatter.config.style_options_panel_border,
                "title": "Arguments",
                "title_align": formatter.config.align_options_panel,
            }

            if isinstance(formatter.config.style_options_panel_box, str):
                box_style = getattr(box, formatter.config.style_options_panel_box, None)
            else:
                box_style = formatter.config.style_options_panel_box

            if box_style:
                kw["box"] = box_style

            formatter.write(Panel(options_table, **kw))


@dataclasses.dataclass
class CommandTreeNode:
    """A tree of command groups/commands."""

    children: dict[str, CommandTreeNode] = dataclasses.field(default_factory=dict)
    """Child nodes of this group."""
    command: Optional[Callable[..., None]] = None
    """Command to execute at this node, if the children are empty."""

    def register_commands(self, parent_click_group: click.Group) -> None:
        """Register the commands to parent's typer group."""
        for child_name, child in self.children.items():
            if child.children:
                children_names = ", ".join(child.children.keys())
                grp = parent_click_group.group(
                    name=child_name, help=f"{children_names}"
                )(lambda: None)
                child.register_commands(grp)
            else:
                assert child.command
                parent_click_group.command(child_name, cls=CommandWithAttributeHelp)(
                    with_errors(child.command)
                )

    def add_command(
        self,
        command_decl: tuple[Callable[..., None]]
        | tuple[str, Callable[..., None]]
        | tuple[str, str, Callable[..., None]],
    ) -> None:
        """Add a command to the tree."""
        if len(command_decl) == 1:
            command = command_decl[0]
            assert not self.command, f"Can not set {command} to node {self}"
            assert not self.children, f"Can not set {command} to node {self}"
            self.command = command
        else:
            command_name = command_decl[0]
            assert isinstance(command_name, str), f"Invalid command name {command_name}"
            if command_name not in self.children:
                self.children[command_name] = CommandTreeNode()
            self.children[command_name].add_command(
                command_decl[1:],
            )


def generate_click_command() -> click.Group:
    """Register all commands into the typer app."""
    app = click.group(name="nrp-cmd")(lambda: None)

    tree_root = CommandTreeNode()
    for cmd in commands:
        # ignore type as mypy says that the function can not be cast to Callable[..., None]
        tree_root.add_command(cmd)  # type: ignore

    tree_root.register_commands(app)

    return app


app = generate_click_command()
"""Typer main application."""


if __name__ == "__main__":
    # call the application if run as a script
    app()
