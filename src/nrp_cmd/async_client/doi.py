#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Resolve DOIs to URLs."""

from yarl import URL

from ..config import Config
from .connection import AsyncConnection


async def resolve_doi(connection: AsyncConnection, doi: str, config: Config) -> str:
    """Resolve a DOI to a record URL."""
    datacite_url = config.datacite_url or "https://api.datacite.org"
    url = URL(f"{datacite_url}/dois/{doi}")
    data = await connection.get(url=url, result_class=dict)
    return data["data"]["attributes"]["url"]
