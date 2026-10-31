"""Pyndoc Markdown Submodule: High-level Pythonic wrapper for Panflute and Pandoc AST.

This package provides a clean, Pythonic abstraction over Panflute AST constructors
with automatic type coercion, whitespace tokenization, and helpful diagnostic
error reporting.
"""

from __future__ import annotations

import logging
from typing import Any

from .blocks import *
from .blocks import __all__ as _blocks_all
from .coercion import *
from .coercion import __all__ as _coercion_all
from .convert import *
from .convert import __all__ as _convert_all
from .inlines import *
from .inlines import __all__ as _inlines_all
from .lists import *
from .lists import __all__ as _lists_all
from .tables import *
from .tables import __all__ as _tables_all

logger = logging.getLogger("pyndoc.markdown")

# Target format state for Pandoc filter execution
TARGET_FORMAT: Any = None

# Dynamically collate unique exports across all submodules
__all__ = list(
    dict.fromkeys([
        "TARGET_FORMAT",
        *_coercion_all,
        *_inlines_all,
        *_blocks_all,
        *_lists_all,
        *_tables_all,
        *_convert_all,
    ])
)
