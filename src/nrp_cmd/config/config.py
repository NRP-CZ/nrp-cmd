#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""User-wide configuration of repositories, usually stored in ~/.nrp/invenio-config.json."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Optional, Self

from attrs import define, field
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn, override
from yarl import URL

from ..converter import converter
from .repository import RepositoryConfig
from .variables import Variables


@define(kw_only=True)
class Config:
    """The configuration of the NRP client as stored in the configuration file."""

    repositories: list[RepositoryConfig] = field(factory=list)
    """Locally known repositories."""

    default_alias: Optional[str] = None
    """The alias of the default repository"""

    per_directory_variables: bool = True
    """Whether to load variables from a .nrp directory in the current directory.
       If set to False, the variables are loaded from the global configuration file
       located in ~/.nrp/variables.json.
    """

    _config_file_path: Optional[Path] = None
    """The path from which the config file was loaded."""

    @classmethod
    def from_file(cls, config_file_path: Optional[Path] = None) -> Self:
        """Load the configuration from a file."""
        if not config_file_path:
            if "NRP_CMD_CONFIG_PATH" in os.environ:
                config_file_path = Path(os.environ["NRP_CMD_CONFIG_PATH"])
            else:
                config_file_path = Path.home() / ".nrp" / "invenio-config.json"

        if config_file_path.exists() and config_file_path.stat().st_size > 0:
            ret = converter.structure(
                json.loads(config_file_path.read_text(encoding="utf-8")), cls
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
        assert path is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(converter.unstructure(self), indent=4))

    #
    # Repository management
    #

    def get_repository(self, alias: str) -> RepositoryConfig:
        """Get a repository by its alias."""
        for repo in self.repositories:
            if repo.alias == alias:
                if not repo.enabled:
                    raise ValueError(f"Repository with alias '{alias}' is disabled")
                return repo
        raise KeyError(f"Repository with alias '{alias}' not found")

    @property
    def default_repository(self) -> RepositoryConfig:
        """Get the default repository."""
        if self.default_alias is None:
            raise ValueError("Default repository not set")
        return self.get_repository(self.default_alias)

    def add_repository(self, repository: RepositoryConfig) -> None:
        """Add a repository to the configuration."""
        self.repositories.append(repository)

    def remove_repository(self, repository: RepositoryConfig | str) -> None:
        """Remove a repository from the configuration."""
        if isinstance(repository, str):
            repository = self.get_repository(repository)
        self.repositories.remove(repository)

    def set_default_repository(self, alias: str) -> None:
        """Set the default repository by its alias."""
        try:
            next(repo for repo in self.repositories if repo.alias == alias)
        except StopIteration:
            raise ValueError(f"Repository with alias '{alias}' not found") from None
        self.default_alias = alias

    def get_repository_from_url(self, record_url: str | URL) -> RepositoryConfig:
        """Get the repository configuration for a given record URL.

        If there is no repository configuration for the given URL, a dummy
        repository configuration is returned.
        """
        record_url = URL(record_url)
        repository_root_url = record_url.with_path("/")
        for repository in self.repositories:
            if not repository.enabled:
                continue
            if repository.url == repository_root_url:
                return repository
        # return a dummy repository configuration
        return RepositoryConfig(
            alias=str(repository_root_url),
            url=repository_root_url,
            info=None,
        )

    def find_repository(self, repository: URL | str) -> RepositoryConfig:
        """Find a repository configuration by its URL or alias name."""

        # try alias first
        if isinstance(repository, str):    
            with contextlib.suppress(KeyError):
                return self.get_repository(repository)
        # if not successful, use the url to get/configure a repository
        return self.get_repository_from_url(repository)

    def load_variables(self) -> Variables:
        """Load the global variables from the configuration file."""
        if self.per_directory_variables:
            return Variables.from_file(Path.cwd() / ".nrp" / "variables.json")
        return Variables.from_file()


config_unst_hook = make_dict_unstructure_fn(
    Config, converter, _config_file_path=override(omit=True)
)
config_st_hook = make_dict_structure_fn(
    Config, converter, _config_file_path=override(omit=True)
)

converter.register_structure_hook(Config, config_st_hook)
converter.register_unstructure_hook(Config, config_unst_hook)
