#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Command line client for updating records."""

from collections.abc import Callable
from functools import partial
from typing import Any, Optional, Self, cast

import rich_click as click
from deepmerge import always_merger
from rich.console import Console

from nrp_cmd.async_client import (
    AsyncRecordsClient,
    get_async_client,
    get_repository_from_record_id,
)
from nrp_cmd.async_client.connection import AsyncConnection
from nrp_cmd.cli.base import OutputWriter, async_command
from nrp_cmd.cli.records.metadata import read_metadata
from nrp_cmd.cli.records.table_formatters import format_record_table
from nrp_cmd.config import Config

from ..arguments import (
    Model,
    Output,
    argument_with_help,
    with_config,
    with_model,
    with_output,
    with_repository,
    with_resolved_vars,
    with_verbosity,
)


@with_config
@with_repository
@with_resolved_vars("record_id")
@with_output
@with_verbosity
@with_model
@argument_with_help("record_id", type=str, help="Record ID")
@argument_with_help("metadata", type=str, help="Metadata")
@click.option("--replace/--merge", default=True, help="Replace or merge the metadata")
@click.option("--path", "-p", type=str, help="Path within the metadata")
@click.option("--model", type=str, help="Model name")
@click.option(
    "--published/--no-published", default=False, help="Include only published records"
)
@click.option("--draft/--no-draft", default=False, help="Include only drafts")
@async_command
async def update_record(
    *,
    config: Config,
    repository: Optional[str],
    record_id: str,
    metadata: str,
    replace: bool = True,
    path: Optional[str] = None,
    model: Model,
    out: Output,
) -> None:
    """Update a record with new metadata."""
    console = Console()

    if record_id.startswith("@"):
        record_id = record_id[1:]
        loaded_record_ids = config.load_variables()[record_id]
        if len(loaded_record_ids) != 1:
            raise ValueError(
                f"Variable {record_id} is not a single record ID: {loaded_record_ids}"
            )
        record_id = loaded_record_ids[0]

    metadata_json = read_metadata(metadata)
    record_url, repository_config = await get_repository_from_record_id(
        AsyncConnection(), record_id, config, repository
    )

    published = model.published
    draft = model.draft

    client = await get_async_client(repository, config=config)

    records_api: AsyncRecordsClient = client.records.draft_records
    if model.model is not None:
        # normally we use draft records, as most of the use cases are for draft records
        records_api = records_api.with_model(model.model)
    if model.model and not model.published and not model.draft:
        # make sure we have models information
        await client.get_repository_info()
        assert repository_config.info, "Repository info is missing"
        assert model.model, "Need to specify a model"
        repository_model = repository_config.info.models[model.model]
        if "drafts" in repository_model.features:
            draft = True
        else:
            published = True

    if published:
        records_api = client.records.published_records
    elif draft:
        records_api = client.records.draft_records

    record = await records_api.read(record_url)
    merge_metadata_at_path(
        record.metadata,
        metadata_json,
        replace,
        path,
    )

    record = await records_api.update(record)

    with OutputWriter(
        out.output,
        out.output_format,
        console,
        partial(format_record_table, verbosity=out.verbosity),  # type: ignore # mypy does not understand this
    ) as printer:
        printer.output(record)


def merge_metadata_at_path(
    metadata: Any,  # noqa: ANN401
    new_metadata: Any,  # noqa: ANN401
    replace: bool,
    path: str | None,
) -> dict[str, Any]:
    """Merge metadata at a path in a nested dictionary/list.

    :param metadata:         the whole metadata into which the new metadata should be merged
    :param new_metadata:     the new metadata to merge at path `path`
    :param replace:          whether to replace the old metadata at the path or merge them
    :param path:             the path to the metadata to merge
    :return:                 modified metadata
    """
    setters = InPathMDSetter.from_path(metadata, path or "")

    old = setters[-1].value
    if replace:
        if isinstance(old, dict):
            old.clear()
            cast(dict[str, Any], old).update(new_metadata)
        elif isinstance(old, list):
            old.clear()
            cast(list[Any], old).extend(new_metadata)
        else:
            old = new_metadata
    else:
        if isinstance(old, dict):
            always_merger.merge(cast(dict[str, Any], old), new_metadata)
        elif isinstance(old, list):
            cast(list[Any], old).extend(new_metadata)
        else:
            old = new_metadata
    setters[-1].value = old
    return setters[0].value


class InPathMDSetter:
    """A class for setting metadata at a path in a nested dictionary/list."""

    def __init__(
        self,
        metadata: dict[str, Any] | list[Any],
        parent: Self | None = None,
        parent_key: str | int | None = None,
    ):
        """Create a new InPathMDSetter object."""
        self.metadata: dict[str, Any] | list[Any] = metadata
        self.parent = parent
        self.parent_key = parent_key

    @classmethod
    def from_path(cls, metadata: dict[str, Any] | list[Any], path: str) -> list[Self]:
        """Create a list of InPathMDSetter objects representing the path to the metadata.

        Each object in the list represents a key in the path to the metadata with a getter
        and setter for the value at that key.
        """
        path_parts = path.split(".") if path else []
        path_parts = [x for x in path_parts if x]
        ret = [cls(metadata)]
        empty_factory: Callable[[], Any]

        def _empty_factory() -> None:
            return None

        for key_idx, key in enumerate(path_parts):

            empty_factory = _empty_factory

            if key_idx < len(path_parts) - 1:
                next_key = path_parts[key_idx + 1]
                empty_factory = list if next_key.isdigit() else dict
            ret.append(ret[-1]._get_key(key, empty_factory))
        return ret

    def _get_key(self, key: str, empty_factory: Callable[[], Any]) -> Self:
        cls: type[Self] = type(self)
        if isinstance(self.metadata, dict):
            if key not in self.metadata:
                return cls(empty_factory(), self, key)
            return cls(self.metadata[key], self, key)
        else:
            if int(key) >= len(self.metadata):
                return cls(empty_factory(), self, key)
            else:
                return cls(self.metadata[int(key)], self, key)

    @property
    def value(self) -> Any:  # noqa: ANN401
        """Get the value of the metadata at the path represented by this object."""
        return self.metadata

    @value.setter
    def value(self, value: Any) -> None:  # noqa: ANN401
        """Set the value of the metadata at the path represented by this object."""
        self.metadata = value
        if self.parent:
            assert self.parent_key is not None
            self.parent._set_key_in_parent(self.parent_key, self.metadata)

    def _set_key_in_parent(self, key: str | int, value: Any) -> None:  # noqa: ANN401
        assert self.parent_key is not None
        if isinstance(self.metadata, dict):
            assert isinstance(key, str)
            self.metadata[key] = value
        else:
            if int(key) < len(self.metadata):
                self.metadata[int(key)] = value
            else:
                self.metadata.append(value)
        if self.parent:
            self.parent._set_key_in_parent(self.parent_key, self.metadata)
