#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""A response that can raise parsed invenio errors."""

import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from aiohttp import ClientResponse

from ...errors import (
    DoesNotExistError,
    RepositoryClientError,
    RepositoryCommunicationError,
    RepositoryRetryError,
    RepositoryServerError,
)


class RepositoryResponse(ClientResponse):
    """A response that can raise parsed invenio errors."""

    async def raise_for_invenio_status(self) -> None:
        """Raise an exception if the response status code is not 2xx.

        :raises RepositoryServerError: if the status code is 5xx
        :raises RepositoryClientError: if the status code is 4xx
        :raises RepositoryCommunicationError: if the status code is not 2xx nor 4xx nor 5xx
        """
        if not self.ok:
            payload_text = await self.text()
            self.release()
            payload: Any
            try:
                payload = json.loads(payload_text)
            except ValueError:
                payload = {
                    "status": self.status,
                    "reason": payload_text,
                }
            if self.status == 429:
                after_seconds: float | None = 20
                retry_after = self.headers.get("Retry-After", None)
                if retry_after:
                    try:
                        after_seconds = float(retry_after)
                    except:
                        try:
                            after_datetime = parsedate_to_datetime(retry_after)
                            after_seconds = (
                                datetime.now() - after_datetime
                            ).total_seconds()
                        except:
                            pass
                raise RepositoryRetryError(after_seconds)

            if self.status >= 500:
                raise RepositoryServerError(self.request_info, payload)
            elif self.status >= 400:
                if self.status == 404:
                    raise DoesNotExistError(self.request_info, payload)
                raise RepositoryClientError(self.request_info, payload)
            raise RepositoryCommunicationError(self.request_info, payload)
