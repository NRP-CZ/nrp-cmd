#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""This package contains classes to work with the configuration of the NRP invenio client.

This configuration is stored in a JSON file
on a file system, usually in .nrp/invenio-config.json.

Normally you'd not use the classes directly, but instantiate the client directly
with get_sync_client / get_async_client functions from the nrp_cmd.client module.

To get a configuration object, you can use the Config.from_file() method
and either pass the path to the configuration file or let it default to ~/.nrp/invenio-config.json.
"""

from .config import Config
from .repository import RepositoryConfig

__all__ = ("Config", "RepositoryConfig")
