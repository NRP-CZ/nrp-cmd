#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Bearer authentication support for aiohttp."""

from typing import Optional

from aiohttp import BasicAuth, ClientRequest, hdrs

from ...types.auth import BearerTokenForHost


class Authentication(BasicAuth):
    """A generic authentication class that can be used to provide different types of authentication."""

    # a little strange to inherit from BasicAuth, but it is the only way to
    # provide different auth types to the ClientRequest

    def apply(self, request: ClientRequest) -> None:
        """Apply the authentication to the request.

        :param request: aiohttp request where the authentication should be applied
        """
        raise NotImplementedError()


class AuthenticatedClientRequest(ClientRequest):
    """Implementation of the ClientRequest that handles different types of authentication (not only BasicAuth)."""

    def update_auth(
        self, auth: Optional[Authentication], trust_env: bool = False
    ) -> None:
        """Override the authentication in the request to allow non-basic auth methods."""
        if not auth or not isinstance(auth, Authentication):
            return super().update_auth(auth, trust_env)

        auth.apply(self)


class BearerAuthentication(Authentication):
    """Bearer authentication class that adds the Bearer token to the request."""

    def __init__(self, tokens: list[BearerTokenForHost]):
        """Create a new BearerAuthentication instance.

        :param tokens: list of (host url, token) pairs. The token will be added to the request if the host url matches
            (including the scheme).
        """
        self.tokens = tokens

    def apply(self, request: ClientRequest) -> None:
        """Apply the authentication to the request.

        :param request: aiohttp request where the authentication should be applied
        """
        for token in self.tokens:
            if (
                request.url.host == token.host_url.host
                and request.url.scheme == token.host_url.scheme
            ):
                request.headers[hdrs.AUTHORIZATION] = f"Bearer {token.token}"
                break
