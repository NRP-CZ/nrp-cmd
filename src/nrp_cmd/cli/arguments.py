import dataclasses
import enum
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Optional

import typer

from nrp_cmd.cli.base import OutputFormat
from nrp_cmd.config import Config

from .argmerge import merge_arguments


class VerboseLevel(enum.Enum):
    """Verbosity level."""

    NORMAL = 0
    QUIET = -1
    VERBOSE = 1


class DebugLevel(enum.Enum):
    """Debug level."""

    NONE = 0
    URL = 1
    REQUEST = 2
    RESPONSE = 3


@dataclasses.dataclass
class Output:
    """Common traits for CLI commands."""

    verbosity: VerboseLevel = VerboseLevel.NORMAL
    progress: bool = False
    output: Optional[Path] = None
    output_format: Optional[OutputFormat] = None


def with_verbosity(func: Callable) -> Callable:
    """Add verbosity and debug options to a command."""

    async def wrapper(
        *,
        verbose: Annotated[
            int,
            typer.Option(
                "--verbose",
                "-v",
                help="Increase verbosity",
                count=True,
                show_default=False,
            ),
        ] = 0,
        quiet: Annotated[
            int,
            typer.Option(
                "--quiet",
                "-q",
                help="Decrease verbosity",
                count=True,
                show_default=False,
            ),
        ] = 0,
        log_url: Annotated[
            bool,
            typer.Option(help="Log urls", show_default=False),
        ] = False,
        log_request: Annotated[
            bool,
            typer.Option(help="Log requests", show_default=False),
        ] = False,
        log_response: Annotated[
            bool,
            typer.Option(help="Log responses", show_default=False),
        ] = False,
        **kwargs,
    ) -> Any:
        out: Output = kwargs.pop("out", None) or Output()
        verbose = verbose - quiet
        match verbose:
            case 0:
                out.verbosity = VerboseLevel.NORMAL
            case _ if verbose > 0:
                out.verbosity = VerboseLevel.VERBOSE
            case _:
                out.verbosity = VerboseLevel.QUIET
        if log_url:
            log = logging.getLogger("nrp_cmd.communication.url")
            log.setLevel(logging.INFO)
        if log_request:
            log = logging.getLogger("nrp_cmd.communication.request")
            log.setLevel(logging.INFO)
        if log_response:
            log = logging.getLogger("nrp_cmd.communication.response")
            log.setLevel(logging.INFO)
        return await func(out=out, **kwargs)

    wrapper.__name__ = "with_verbosity"
    return merge_arguments(wrapper, func)


def with_setvar(func: Callable) -> Callable:
    """Add a variable to store the result of the command."""

    async def wrapper(
        *,
        variable: Annotated[
            Optional[str],
            typer.Option("--set", help="Store the result URL(s) in a variable"),
        ] = None,
        **kwargs,
    ) -> Any:
        if variable and variable.startswith("@"):
            variable = variable[1:]
        return await func(variable=variable, **kwargs)

    wrapper.__name__ = "with_setvar"
    return merge_arguments(wrapper, func)


def with_output(func: Callable) -> Callable:
    """Add output options to a command."""

    async def wrapper(
        *,
        output: Annotated[
            Optional[Path], typer.Option("-o", help="Save the output to a file")
        ] = None,
        output_format: Annotated[
            Optional[OutputFormat],
            typer.Option("-f", help="The format of the output"),
        ] = None,
        **kwargs,
    ) -> Any:
        out = kwargs.pop("out", None) or Output()
        out.output = output
        out.output_format = output_format
        return await func(out=out, **kwargs)

    wrapper.__name__ = "with_output"
    return merge_arguments(wrapper, func)


def with_progress(func: Callable) -> Callable:
    """Add a progress bar to a command."""

    async def wrapper(
        *,
        progress: Annotated[bool, typer.Option(help="Show progress bar")] = True,
        **kwargs,
    ) -> Any:
        out = kwargs.pop("out", None) or Output()
        out.progress = progress
        return await func(out=out, **kwargs)

    wrapper.__name__ = "with_progress"
    return merge_arguments(wrapper, func)


def with_config(func: Callable) -> Callable:
    """Add a config object to a command."""

    async def wrapper(
        *,
        config: Annotated[
            Optional[Path], typer.Option("--config-path", show_default=False)
        ] = None,
        **kwargs: Any,
    ) -> Any:
        _config = Config.from_file(config)
        return await func(config=_config, **kwargs)

    wrapper.__name__ = "with_config"
    return merge_arguments(wrapper, func)

def with_repository(func: Callable) -> Callable:

    async def wrapper(
        *,
        repository: Annotated[Optional[str], typer.Option(help="Repository alias")] = None,
        **kwargs: Any,
    ) -> Any:
        return await func(repository=repository, **kwargs)

    wrapper.__name__ = "with_repository"
    return merge_arguments(wrapper, func)

def with_resolved_vars(argument_name):
    def decorator(func):
        async def wrapper(
            **kwargs,
        ) -> Any:
            if argument_name not in kwargs:
                raise ValueError(f"Argument {argument_name} not found in kwargs {kwargs}")
            config = kwargs.get("config")
            if not config:
                raise ValueError(f"Config not found in kwargs {kwargs}")
            variables = config.load_variables()
            if isinstance(kwargs[argument_name], list):
                resolved = []
                for arg in kwargs[argument_name]:
                    if arg.startswith("@"):
                        resolved.extend(variables[arg[1:]])
                    else:
                        resolved.append(arg)
            else:
                arg = kwargs[argument_name]
                if arg.startswith("@"):
                    resolved = config.load_variables()[arg[1:]]
                    if len(resolved) != 1:
                        raise ValueError(f"Variable {arg} has many values: {resolved}")
                    resolved = resolved[0]
                else:
                    resolved = arg

            kwargs[argument_name] = resolved
            return await func(**kwargs)

        wrapper.__name__ = "with_resolved_vars"
        return merge_arguments(wrapper, func)

    return decorator