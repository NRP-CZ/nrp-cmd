#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Resolve DOIs to URLs."""

from yarl import URL

from .connection import AsyncConnection


async def resolve_doi(connection: AsyncConnection, doi: str) -> str:
    """Resolve a DOI to a record URL."""
    data = await connection.get(url=URL(f"https://api.datacite.org/dois/{doi}"), result_class=dict)
    return data["data"]["attributes"]["url"]
