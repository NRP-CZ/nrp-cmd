#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""CLI for requests."""

from .accept import accept_request
from .cancel import cancel_request
from .create import create_request
from .decline import decline_request
from .list import list_requests
from .submit import submit_request

__all__ = (
    "list_requests",
    "create_request",
    "accept_request",
    "decline_request",
    "cancel_request",
    "submit_request",
)
