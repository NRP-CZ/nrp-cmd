#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Helper methods to create output file names from path templates."""

from pathlib import Path
from typing import Any

from nrp_cmd.cli.base import OutputFormat
from nrp_cmd.converter import converter


def create_output_file_name(
    output_name: Path,
    obj_id: str,
    obj: Any,
    output_format: OutputFormat | None,
    **kwargs: Any,  # noqa: ANN401
) -> Path:
    """Create an output file name from a template."""
    # output name can contain variables inside {}. If it does, we will replace them with the values
    # from the record
    # we need to make sure that the expanded output name does not contain illegal combinations,
    # such as /../ or /./ or leading '/' - we strip them if that is the case

    output_parts: tuple[str, ...] = output_name.parts if output_name else ()
    is_absolute = output_name.is_absolute()

    transformed_parts = [
        format_part(part, obj_id, obj, output_format or OutputFormat.JSON, **kwargs)
        for part in output_parts
    ]
    transformed_parts = [part.replace("/", "") for part in transformed_parts]
    transformed_parts = [part.replace("\\", "") for part in transformed_parts]
    transformed_parts = [part.replace("..", "") for part in transformed_parts]
    transformed_parts = [part for part in transformed_parts if part]

    if is_absolute:
        output_name = Path("/", *transformed_parts)
    else:
        output_name = Path(*transformed_parts).absolute()

    return output_name


def format_part(
    part: str,
    obj_id: str,
    obj: Any,
    output_format: OutputFormat,
    **kwargs: Any,  # noqa: ANN401
) -> str:
    """Format a part of the output name.

    The part can contain variables in the form of {variable_name}. If the part contains
    both '{' and '}', it is considered a template and it will be formatted with the
    variables from the record and the kwargs.
    """
    if "{" in part and "}" in part:
        options: dict[str, str] = {
            "id": obj_id,
            "ext": f".{output_format.value}" if output_format else "table",
            **(converter.unstructure(obj) if obj else {}),
            **kwargs,
        }
        return part.format(**options)
    return part
