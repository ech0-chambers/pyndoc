"""Pandoc conversion utilities and preprocessor integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import panflute as pf

logger = logging.getLogger("pyndoc.markdown.convert")

__all__ = ["convert_from_string"]


def convert_from_string(
    text: str,
    preprocess: bool = False,
    output_format: str | None = "panflute",
    **kwargs: Any,
) -> str | list[pf.Element]:
    """Convert a markdown string to Panflute AST elements or target markup."""
    if "format" in kwargs:
        output_format = kwargs.pop("format")

    if preprocess:
        from pyndoc.preprocess import preprocess as preprocess_text

        if output_format != "panflute":
            text = preprocess_text(text, target_format=output_format)
        else:
            text = preprocess_text(text)

    # Filter file is located at pyndoc/filter.py
    filter_file = Path(__file__).parent.parent / "filter.py"
    if not filter_file.exists():
        raise FileNotFoundError(f"Filter file not found: {filter_file}")

    output = pf.convert_text(
        text,
        input_format="markdown",
        extra_args=[f"--filter={filter_file.resolve().absolute()}"],
        standalone=False,
        output_format=output_format,
    )
    logger.debug(f"Output from markdown conversion: {output}")
    return output
