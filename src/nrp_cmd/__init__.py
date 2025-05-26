"""# NRP Commandline Tools and Python Client

## Overview

This package provides a set of libraries and command-line tools for interacting
with repositories that conform to the Czech National Repository Platform.
Although support currently focuses on InvenioRDM-based repositories, the
architecture is designed to be easily extensible to other repository types.

## Configuration

The package uses a configuration file stored in the user's home directory under
the `.nrp` folder. You can add a new repository to the configuration by running:

```bash
nrp-cmd add repository https://my-repository.org [--alias my-repo]
```

This command will guide you through setting up the repository URL and any
required authentication tokens. If you prefer not to use the built-in
configuration mechanism, you can provide the necessary parameters directly
to the client.

## API

This package offers both synchronous and asynchronous clients for working
with the configured repositories. Choose the asynchronous client if you have
an asyncio-based application or need higher performance for data transfers.
For simpler applications, the synchronous client is often sufficient.

Both clients share the same high-level API, allowing you to switch between them
easily (with the appropriate `async`/`await` adjustments as needed).

## Example

A simple script that searches for records containing the word "Einstein" in metadata
and downloads all matching records to a local directory. By default it will download
data in 10 concurrent connections (see :func:`nrp_cmd.get_async_client` for more details).

```python
from nrp_cmd import get_async_client
from nrp_cmd.async_client import AsyncRepositoryClient, download

async def run():
    client: AsyncRepositoryClient = await get_async_client("my-repo")
    client: AsyncRepositoryClient = await get_async_client("https://my-repository.org")

    async for record in client.records.scan(q="Einstein"):
        print(record.metadata)
        # and store the record together with files in a directory for further processing
        download(record, f"/path/to/download/{record.id}", with_files=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
```

See :class:`nrp_cmd.async_client.base_client.AsyncRepositoryClient` for more details.

"""

from .async_client import get_async_client
from .sync_client import get_sync_client

__all__ = (
    "get_async_client",
    "get_sync_client",
)
