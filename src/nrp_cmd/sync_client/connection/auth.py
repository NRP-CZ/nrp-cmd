#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Authentication for the synchronous client."""

import requests.auth
from yarl import URL

from ...types.auth import BearerTokenForHost


class BearerAuthentication(requests.auth.AuthBase):
    """Bearer token authentication for requests."""

    def __init__(self, tokens: list[BearerTokenForHost]):
        """Initialize the authentication with the tokens."""
        self.tokens = tokens

    def __call__(self, r: requests.Request) -> requests.Request:
        """Add the Authorization header to the request."""
        url = URL(r.url)

        for token in self.tokens:
            if url.host == token.host_url.host and url.scheme == token.host_url.scheme:
                r.headers["Authorization"] = f"Bearer {token.token}"
                break
        return r
