"""Bearer token for the invenio repository."""

import dataclasses

from yarl import URL


@dataclasses.dataclass
class BearerTokenForHost:
    """URL and bearer token for the invenio repository."""

    host_url: URL
    """URL of the repository."""

    token: str
    """Bearer token for the repository."""

    def __post_init__(self):
        """Cast the host_url to URL if it is not already."""
        if not isinstance(self.host_url, URL):
            self.host_url = URL(self.host_url)
        assert self.token is not None, "Token must be provided"

