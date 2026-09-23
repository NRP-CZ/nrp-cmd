#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Authentication for the synchronous client."""

import requests.auth
from requests_kerberos import HTTPKerberosAuth
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


class KerberosAuthentication(requests.auth.AuthBase):
    """Kerberos (SPNEGO/Negotiate) authentication scoped to the configured hosts.

    The Kerberos token is only attached to requests whose host and scheme match one of
    the configured host urls, so that it is never sent to third-party hosts (such as
    pre-signed S3 urls). Mutual authentication is disabled to match the behaviour of the
    asynchronous client, which cannot verify the server's Negotiate response.
    """

    def __init__(self, host_urls: list[URL]):
        """Initialize the authentication with the hosts it applies to."""
        self.host_urls = host_urls
        self._kerberos_auth = HTTPKerberosAuth(force_preemptive=True
        )

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Apply Kerberos authentication if the request targets one of the known hosts."""
        url = URL(str(r.url))
        for host_url in self.host_urls:
            if url.host == host_url.host and url.scheme == host_url.scheme:
                return self._kerberos_auth(r)
        return r
