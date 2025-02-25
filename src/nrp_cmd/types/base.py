#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Base types for invenio REST responses."""

from __future__ import annotations

from typing import Any


class Model:
    """Base model, which allows getting extra fields via normal dot operator."""

    _extra_data: dict[str, Any]

    def __getattr__(self, item: str) -> Any:  # noqa: ANN401
        """Get extra fields from the model_extra attribute."""
        if "_extra_data" not in self.__dict__:
            self._extra_data: dict[str, Any] = {}

        if item in self._extra_data:
            return self._extra_data[item]
        dash_item = item.replace("_", "-")
        if dash_item in self._extra_data:
            return self._extra_data[dash_item]

        raise AttributeError(f"{self.__class__.__name__} has no attribute {item}")

    def __getitem__(self, item: str) -> Any:
        """Get extra fields from the model_extra attribute."""
        return getattr(self, item)
