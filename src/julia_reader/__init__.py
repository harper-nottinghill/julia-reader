"""Julia Reader — standalone progressive Reader Chronicle harness."""

from __future__ import annotations

from .pipeline import run_reader
from .reader_config import PipelineConfig, ReaderPaths

__all__ = ["run_reader", "PipelineConfig", "ReaderPaths"]
__version__ = "0.1.0"
