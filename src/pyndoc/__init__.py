"""Pyndoc: A standalone Pandoc filter and preprocessor for build-time Python execution.

Pyndoc allows executing arbitrary Python code inside Markdown documents at build time,
rendering mathematical formulas via an AST LaTeX generator, formatting Pint physical
units, and building structured Panflute documents.
"""

from __future__ import annotations

from .formats import Format
from .preprocess import preprocess
from .timer import Timer

__version__ = "0.2.0"

__all__ = [
    "Format",
    "Timer",
    "__version__",
    "preprocess",
]
