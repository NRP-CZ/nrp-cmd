#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""Data sources and sinks."""

from .base import DataSink, DataSource, InputStream, OutputStream, SinkState
from .file import FileSink, FileSource
from .memory import MemorySink, MemorySource
from .stdin import StdInDataSource

__all__ = (
    "DataSink",
    "DataSource",
    "SinkState",
    "InputStream",
    "OutputStream",
    "MemorySink",
    "MemorySource",
    "FileSink",
    "FileSource",
    "StdInDataSource",
)