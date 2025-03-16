import dataclasses
import enum
import functools
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, overload

import rich_click as click
import yaml
from click.exceptions import Exit

from nrp_cmd.config import Config
from nrp_cmd.errors import RepositoryClientError, RepositoryError, RepositoryJSONError


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


class OutputFormat(enum.Enum):
    """Output format."""

    JSON = "json"
    JSON_LINES = "jsonl"
    YAML = "yaml"
    TABLE = "table"

    def __str__(self):
        """Return the value of the enum."""
        return self.value


@dataclasses.dataclass
class Model:
    draft: bool
    published: bool

    model: Optional[str] = None
    community: Optional[str] = None
    workflow: Optional[str] = None


type ClickCommand = Callable[..., None]


class Argument(click.Argument):
    """A :class:`click.Argument` with help text."""

    def __init__(self, *args: Any, help: str | None = None, **attrs: Any):
        super().__init__(*args, **attrs)
        self.help = help

    def get_argument_help_record(
        self, ctx: click.Context
    ) -> tuple[str, str, str] | None:
        if self.name and self.help:
            return self.name, "" if self.required else "optional", self.help or ""
        return None


argument_with_help = functools.partial(click.argument, cls=Argument)

@dataclasses.dataclass
class Output:
    """Common traits for CLI commands."""

    verbosity: VerboseLevel = VerboseLevel.NORMAL
    progress: bool = False
    output: Optional[Path] = None
    output_format: Optional[OutputFormat] = None


@overload
def with_verbosity(
    arg: VerboseLevel,
) -> Callable[[ClickCommand], ClickCommand]: ...


@overload
def with_verbosity(
    arg: ClickCommand,
) -> ClickCommand: ...


def with_verbosity(
    arg: VerboseLevel | ClickCommand,
) -> Callable[[ClickCommand], ClickCommand] | ClickCommand:
    """Add verbosity and debug options to a command."""
    default_level = arg if isinstance(arg, VerboseLevel) else VerboseLevel.NORMAL

    def decorator(func: ClickCommand) -> ClickCommand:

        @click.option("--verbose", "-v", count=True, help="Increase verbosity")
        @click.option("--quiet", "-q", count=True, help="Decrease verbosity")
        @click.option("--log-url", is_flag=True, help="Log urls")
        @click.option("--log-request", is_flag=True, help="Log requests")
        @click.option("--log-response", is_flag=True, help="Log responses")
        @functools.wraps(func)
        def wrapper(
            verbose: int = 0,
            quiet: int = 0,
            log_url: bool = False,
            log_request: bool = False,
            log_response: bool = False,
            **kwargs: Any,
        ) -> None:
            out: Output = kwargs.pop("out", None) or Output()
            verbose = default_level.value + verbose - quiet
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
            func(out=out, **kwargs)

        wrapper.__name__ += "_with_output"
        return wrapper

    if isinstance(arg, VerboseLevel):
        return decorator
    return decorator(arg)


def with_setvar(func: ClickCommand) -> ClickCommand:
    """Add a variable to store the result of the command."""

    @click.option(
        "--set",
        "variable",
        help="Store the result URL(s) in a variable",
    )
    @functools.wraps(func)
    def wrapper(
        variable: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if variable and variable.startswith("@"):
            variable = variable[1:]
        func(variable=variable, **kwargs)

    wrapper.__name__ += "_with_setvar"
    return wrapper


def with_output(func: ClickCommand) -> ClickCommand:
    """Add output options to a command."""

    @click.option(
        "-o",
        "--output",
        help="Save the output to a file",
        type=click.Path(),
    )
    @click.option(
        "-f",
        "--output-format",
        help="The format of the output",
        type=click.Choice([str(f) for f in OutputFormat]),
    )
    @functools.wraps(func)
    def wrapper(
        output: Optional[Path] = None,
        output_format: Optional[OutputFormat] = None,
        **kwargs: Any,
    ) -> None:
        out = kwargs.pop("out", None) or Output()
        out.output = Path(output) if output else None
        out.output_format = OutputFormat(output_format) if output_format else None
        func(out=out, **kwargs)

    wrapper.__name__ += "_with_output"
    return wrapper


def with_progress(func: ClickCommand) -> ClickCommand:
    """Add a progress bar to a command."""

    @click.option(
        "--progress/--no-progress",
        default=True,
        help="Show progress bar",
    )
    @functools.wraps(func)
    def wrapper(
        progress: bool = True,
        **kwargs: Any,
    ) -> None:
        out = kwargs.pop("out", None) or Output()
        out.progress = progress
        func(out=out, **kwargs)

    wrapper.__name__ += "_with_progress"
    return wrapper


def with_config(func: ClickCommand) -> ClickCommand:
    """Add a config object to a command."""

    @click.option(
        "--config-path",
        help="Path to the configuration file",
        type=click.Path(dir_okay=False, exists=True),
    )
    @functools.wraps(func)
    def wrapper(
        config_path: Optional[Path] = None,
        **kwargs: Any,
    ) -> None:
        _config = Config.from_file(config_path)
        func(config=_config, **kwargs)

    wrapper.__name__ += "_with_config"
    return wrapper


def with_repository(func: ClickCommand) -> ClickCommand:
    @click.option(
        "--repository",
        help="Repository alias",
    )
    @functools.wraps(func)
    def wrapper(
        repository: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        func(repository=repository, **kwargs)

    wrapper.__name__ += "_with_repository"
    return wrapper


def with_resolved_vars(argument_name: str) -> Callable[[ClickCommand], ClickCommand]:
    """Resolve variables in the command arguments."""

    def decorator(func: ClickCommand) -> ClickCommand:

        @functools.wraps(func)
        def wrapper(
            **kwargs: Any,
        ) -> Any:
            if argument_name not in kwargs:
                raise ValueError(f"Argument {argument_name} not found in kwargs {kwargs}")
            config: Config | None = kwargs.get("config")
            if not config:
                raise ValueError(f"Config not found in kwargs {kwargs}")
            variables = config.load_variables()
            resolved: list[str] | str
            if isinstance(kwargs[argument_name], (list, tuple)):
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
            func(**kwargs)

        wrapper.__name__ += "_with_resolved_vars"
        return wrapper

    return decorator


@overload
def with_model(
    func: None = None,
    *,
    model: bool = True,
    community: bool = False,
    workflow: bool = False,
    draft: bool = True,
    published: bool = True,
) -> Callable[[ClickCommand], ClickCommand]: ...


@overload
def with_model(
    func: ClickCommand,
    *,
    model: bool = True,
    community: bool = False,
    workflow: bool = False,
    draft: bool = True,
    published: bool = True,
) -> ClickCommand: ...


def with_model(
    func: ClickCommand | None = None,
    *,
    model: bool = True,
    community: bool = False,
    workflow: bool = False,
    draft: bool = True,
    published: bool = True,
) -> Callable[[ClickCommand], ClickCommand] | ClickCommand:
    """Add model options to a command."""

    def decorator(func: ClickCommand) -> ClickCommand:

        @functools.wraps(func)
        def wrapper(
            *,
            model: Optional[str] = None,
            community: Optional[str] = None,
            workflow: Optional[str] = None,
            draft: bool = False,
            published: bool = True,
            **kwargs: Any,
        ) -> None:
            _model = Model(
                model=model,
                community=community,
                workflow=workflow,
                draft=draft,
                published=published,
            )
            func(model=_model, **kwargs)

        if model:
            wrapper = click.option("--model", help="Model name")(wrapper)
        if community:
            wrapper = click.option("--community", help="Community name")(wrapper)
        if workflow:
            wrapper = click.option("--workflow", help="Workflow name")(wrapper)
        if draft:
            wrapper = click.option(
                "--draft/--no-draft", default=False, help="Include only drafts"
            )(wrapper)
        if published:
            wrapper = click.option(
                "--published/--no-published",
                default=False,
                help="Include only published records",
            )(wrapper)

        wrapper.__name__ += "_with_model"
        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def with_record_ids(func: ClickCommand) -> ClickCommand:
    """Add record IDs to a command."""

    @argument_with_help("record_ids", type=str, nargs=-1, help="Record ID(s)")
    @functools.wraps(func)
    def wrapper(
        record_ids: list[str],
        **kwargs: Any,
    ) -> None:
        func(record_ids=record_ids, **kwargs)

    wrapper.__name__ += "_with_record_ids"
    return with_resolved_vars("record_ids")(wrapper)


def _print_error(e: Exception) -> None:
    if isinstance(e, ExceptionGroup):
        for e in e.exceptions:
            _print_error(e)
    elif isinstance(e, RepositoryJSONError):

        if "message" in e.json:
            click.secho(
                f"Client error: {e.json['message']} ({e.json.get('status', 'unknown status')})",
                err=True,
                fg="red",
            )
            click.secho(f"  {e.request_info.url}", err=True, fg="yellow")
        else:
            click.secho(f"Client error: {e.request_info.url}", err=True, fg="red")
        if "errors" in e.json:
            if isinstance(e.json["errors"], list):
                for error in e.json["errors"]:
                    if (
                        isinstance(error, dict)
                        and "field" in error
                        and "messages" in error
                    ):
                        click.secho(f"  {error['field']}:", err=True)
                        click.secho(
                            "    " + "\n    ".join(error["messages"]),
                            err=True,
                            fg="red",
                        )
                    else:
                        yaml.safe_dump(error, sys.stderr)
            else:
                yaml.safe_dump(e.json, sys.stderr)
        else:
            yaml.safe_dump(e.json, sys.stderr)
    elif isinstance(e, RepositoryClientError):
        click.echo(f"Client error: {e}", err=True)
    elif isinstance(e, RepositoryError):
        click.echo(f"Repository error: {e}", err=True)
    else:
        click.echo(f"Error: {e}", err=True)


def with_errors(func: ClickCommand) -> ClickCommand:
    """Add error handling to a command."""

    @click.option(
        "--log-stacktrace", is_flag=True, help="Log stack traces in case of error"
    )
    @functools.wraps(func)
    def wrapper(
        log_stacktrace: bool = False,
        **kwargs: Any,
    ) -> None:
        try:
            func(**kwargs)
        except ExceptionGroup as eg:
            _print_error(eg)
            if log_stacktrace:
                raise
            raise Exit(1) from None
        except Exception as e:
            _print_error(e)
            if log_stacktrace:
                raise
            raise Exit(1) from None

    wrapper.__name__ += "_with_errors"
    return wrapper
