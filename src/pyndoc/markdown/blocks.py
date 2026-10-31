"""Panflute Block AST constructors with automatic type coercion.

This module provides high-level constructors for Block-level Panflute elements
(e.g. `Para`, `Header`, `BlockQuote`, `CodeBlock`, `HorizontalRule`, `Figure`,
`Div`).
"""

from __future__ import annotations

import logging
from typing import Any

import panflute as pf

from pyndoc.markdown.coercion import (
    PanfluteValueError,
    as_blocks,
    as_inlines,
    clean_attributes,
    clean_classes,
    clean_identifier,
    raw_block,
)

logger = logging.getLogger("pyndoc.markdown.blocks")

__all__ = [
    "block_quote",
    "code_block",
    "div",
    "figure",
    "figure_caption",
    "header",
    "horizontal_rule",
    "paragraph",
    "plain",
    "raw",
    "raw_block",
    "rule",
]


def paragraph(*contents: Any) -> pf.Para:
    """Create a paragraph block containing inlines or plain text."""
    inlines = as_inlines(*contents, caller="paragraph")
    return pf.Para(*inlines)


# Backwards compatibility alias
para = paragraph


def plain(*contents: Any) -> pf.Plain:
    """Create a Plain block without paragraph spacing (e.g. for list items)."""
    inlines = as_inlines(*contents, caller="plain")
    return pf.Plain(*inlines)


def header(
    *contents: Any,
    level: int = 1,
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
) -> pf.Header:
    """Create a heading block element.

    Parameters
    ----------
    *contents : Any
        Heading text or inline elements.
    level : int, default=1
        Heading depth (1 to 6).
    identifier : str, optional
        Unique heading ID for anchor links.
    """
    if not (1 <= level <= 6):
        raise PanfluteValueError(
            parameter="level",
            received=level,
            valid_options=["1", "2", "3", "4", "5", "6"],
            container="header",
            problem=f"Heading level must be between 1 and 6, but got {level}.",
            solution="Specify an integer between 1 (top-level title) and 6 (sub-heading).",
        )

    inlines = as_inlines(*contents, caller="header")
    return pf.Header(
        *inlines,
        level=level,
        identifier=clean_identifier(identifier),
        classes=clean_classes(classes),
        attributes=clean_attributes(attributes),
    )


def block_quote(*contents: Any) -> pf.BlockQuote:
    """Create a block quote container from blocks, inlines, or text."""
    blocks = as_blocks(*contents, caller="block_quote")
    return pf.BlockQuote(*blocks)


def code_block(
    text: str,
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
    language: str | None = None,
) -> pf.CodeBlock:
    """Create a fenced code block."""
    norm_classes = clean_classes(classes)
    if language:
        norm_classes.insert(0, language.lstrip("."))
    # Workaround: Panflute sometimes requires a non-empty class or empty string
    if not norm_classes:
        norm_classes = [""]

    return pf.CodeBlock(
        text=str(text),
        identifier=clean_identifier(identifier),
        classes=norm_classes,
        attributes=clean_attributes(attributes),
    )


def horizontal_rule() -> pf.HorizontalRule:
    """Create a horizontal divider rule."""
    return pf.HorizontalRule()


# Backwards compatibility alias
rule = horizontal_rule


def div(
    *contents: Any,
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
) -> pf.Div:
    """Create a fenced Div block container (e.g. for custom Pandoc CSS classes)."""
    blocks = as_blocks(*contents, caller="div")
    return pf.Div(
        *blocks,
        identifier=clean_identifier(identifier),
        classes=clean_classes(classes),
        attributes=clean_attributes(attributes),
    )


def figure_caption(
    *contents: Any,
    short_caption: Any = None,
) -> pf.Caption:
    """Create a figure or table Caption element."""
    if len(contents) == 1 and isinstance(contents[0], pf.Caption):
        return contents[0]

    inlines = as_inlines(*contents, caller="figure_caption")
    short_inlines = as_inlines(short_caption, caller="figure_caption") if short_caption else []
    return pf.Caption(pf.Plain(*inlines), short_caption=short_inlines)


def figure(
    url: str,
    *caption: Any,
    short_caption: Any = None,
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
    image_options: dict[str, Any] | None = None,
) -> pf.Figure:
    """Create a standalone Figure containing an image and optional caption."""
    img_opts = image_options or {}
    img = pf.Image(url=str(url), **img_opts)

    cap_element = None
    if caption:
        if len(caption) == 1 and isinstance(caption[0], pf.Caption):
            cap_element = caption[0]
        else:
            cap_element = figure_caption(*caption, short_caption=short_caption)

    return pf.Figure(
        pf.Plain(img),
        caption=cap_element,
        identifier=clean_identifier(identifier),
        classes=clean_classes(classes),
        attributes=clean_attributes(attributes),
    )


def raw(
    text: str,
    format: str | None = None,
    inline: bool = False,
) -> pf.RawBlock | pf.RawInline:
    """Insert raw target markup (HTML, LaTeX, etc.)."""
    if inline:
        from pyndoc.markdown.coercion import raw_inline

        return raw_inline(text, format=format)
    return raw_block(text, format=format)
