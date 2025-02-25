#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Low-level compatibility layer for file operations."""

import asyncio
import base64
import hashlib
import os
from pathlib import Path
from typing import Literal, overload

import aiofiles
import aiofiles.os

from .base import InputStream, OutputStream


class FileInputStream(InputStream):
    async def seek(self, offset: int, whence: int = os.SEEK_SET) -> None:
        """Change the stream position."""
        ...
        
class FileOutputStream(OutputStream):
    async def seek(self, offset: int, whence: int = os.SEEK_SET) -> None:
        """Change the stream position."""
        ...

    async def truncate(self, size: int) -> None:
        ...
        
@overload
async def open_file(_fpath: Path, mode: Literal["rb"]) -> FileInputStream:
    ...

@overload
async def open_file(_fpath: Path, mode: Literal["wb"] | Literal["r+b"]) -> FileOutputStream:
    ...

async def open_file(_fpath: Path, mode: Literal["rb"] | Literal["wb"] | Literal["r+b"]) -> FileInputStream | FileOutputStream:
    """Open a file for reading or writing."""
    r: FileInputStream | FileOutputStream = await aiofiles.open(_fpath, mode=mode)  # noqa # type: ignore
    return r


async def file_stat(_fpath: Path) -> os.stat_result:
    """Get file statistics."""
    return await aiofiles.os.stat(_fpath)


async def checksum_file(
    file_name: Path, algo: str = "md5", offset: int = 0, count: int | None = None
) -> str:
    """Calculate the checksum of the file."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _checksum, file_name, algo, offset, count)


def _checksum(file_name: Path, algo: str, offset: int, count: int | None) -> str:
    """Calculate the checksum of the data."""
    # cpu-bound operation - run in a separate thread synchronously
    with open(file_name, mode="rb") as f:
        if offset > 0:
            f.seek(offset)

        hasher = hashlib.new(algo)
        chunk_size = get_filesystem_block_size(file_name) * 16

        while count != 0:
            chunk = f.read(min(chunk_size, count or chunk_size))
            if not chunk:
                break
            hasher.update(chunk)
            if count is not None:
                count -= len(chunk)

        return base64.b64encode(hasher.digest()).decode("ascii")


def get_filesystem_block_size(file_path: Path) -> int:
    if hasattr(os, "statvfs"):  # Unix-like systems
        statvfs = os.statvfs(str(file_path))
        return statvfs.f_bsize
    else:
        return 4096  # default block size for Windows


__all__ = (
    "open_file",
    "file_stat",
    "FileInputStream",
    "FileOutputStream",
    "checksum_file",
)
