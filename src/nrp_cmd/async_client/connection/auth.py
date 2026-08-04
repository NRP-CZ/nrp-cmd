#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Bearer and Kerberos authentication support for aiohttp."""

from aiohttp import BasicAuth, ClientRequest, hdrs
from requests_kerberos import HTTPKerberosAuth
from yarl import URL

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

    def update_auth(self, auth: Authentication | None, trust_env: bool = False) -> None:
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


class KerberosAuthentication(Authentication):
    """Kerberos (SPNEGO/Negotiate) authentication that adds a preemptive Authorization header."""

    def __init__(self, host_urls: list[URL]):
        """Create a new KerberosAuthentication instance.

        :param host_urls: list of host urls. The Negotiate header will be added to the request
            only if the request's host url matches one of these (including the scheme), so that
            Kerberos tokens are never sent to third-party hosts (such as pre-signed S3 urls).
        """
        self.host_urls = host_urls

    def apply(self, request: ClientRequest) -> None:
        """Apply preemptive Kerberos Negotiate authentication to the request.

        :param request: aiohttp request where the authentication should be applied
        """
        if not any(
            request.url.host == host_url.host and request.url.scheme == host_url.scheme
            for host_url in self.host_urls
        ):
            return
        auth = HTTPKerberosAuth()
        request.headers[hdrs.AUTHORIZATION] = auth.generate_request_header(
            None, request.url.host, is_preemptive=True
        )
