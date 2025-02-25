#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Variables mainly for storing record urls."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from attrs import define, field

from ..converter import converter


@define(kw_only=True)
class Variables:
    """Variables for the commandline tools."""

    variables: dict[str, list[str]] = field(factory=dict)
    """Internal dictionary of variables."""

    _config_file_path: Optional[Path] = None
    """Path to the configuration file from which the variables have been loaded."""

    class Config:  # noqa
        extra = "forbid"

    @classmethod
    def from_file(cls, config_file_path: Optional[Path] = None) -> "Variables":
        """Load the configuration from a file."""
        if not config_file_path:
            config_file_path = Path.home() / ".nrp" / "variables.json"

        if config_file_path.exists():
            ret = converter.structure(
                json.loads(config_file_path.read_text(encoding="utf-8")),
                cls
            )
        else:
            ret = cls()
        ret._config_file_path = config_file_path
        return ret

    def save(self, path: Optional[Path] = None) -> None:
        """Save the configuration to a file, creating parent directory if needed."""
        if path:
            self._config_file_path = path
        else:
            path = self._config_file_path
        assert path, "No path to save the configuration to."
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(converter.unstructure(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def __getitem__(self, key: str) -> list[str]:
        """Get the value of a variable, raising KeyError if the variable has not been found."""
        try:
            return self.variables[key]
        except KeyError as err:
            raise KeyError(
                f"Variable {key} not found at {self._config_file_path}"
            ) from err

    def __setitem__(self, key: str, value: list[str]):
        """Set the value of a variable."""
        self.variables[key] = value

    def __delitem__(self, key: str):
        """Delete a variable."""
        del self.variables[key]

    def get(self, key: str, default: list[str] | None = None) -> list[str] | None:
        """Get the value of a variable, returning None if the variable has not been found."""
        return self.variables.get(key, default)

    def items(self) -> Iterable[tuple[str, list[str]]]:
        """Return the variables as an iterable of (key, value)."""
        return self.variables.items()
