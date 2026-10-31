"""Panflute Inline AST constructors with automatic type coercion.

This module provides high-level wrappers for Panflute Inline elements (e.g.
`Strong`, `Emph`, `Math`, `Link`, `Code`, `Span`). All functions automatically
coerce Python strings, numbers, LaTeX tokens, and nested inlines without the
unpacking crashes present in legacy wrappers.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from typing import Any

import panflute as pf

from pyndoc.markdown.coercion import (
    as_inlines,
    clean_attributes,
    clean_classes,
    clean_identifier,
    raw_inline,
    string,
)

logger = logging.getLogger("pyndoc.markdown.inlines")

__all__ = [
    "bold",
    "citation",
    "cite",
    "code",
    "equation",
    "footnote",
    "image",
    "inline_math",
    "italic",
    "link",
    "math",
    "raw_inline",
    "small_caps",
    "span",
    "strikethrough",
    "string",
    "subscript",
    "superscript",
    "underline",
]


def bold(*contents: Any) -> pf.Strong:
    """Create bold (strong) text from strings, inlines, or nested iterables."""
    inlines = as_inlines(*contents, caller="bold")
    return pf.Strong(*inlines)


def italic(*contents: Any) -> pf.Emph:
    """Create italic (emphasized) text from strings, inlines, or nested iterables."""
    inlines = as_inlines(*contents, caller="italic")
    return pf.Emph(*inlines)


def strikethrough(*contents: Any) -> pf.Strikeout:
    """Create strikethrough (strikeout) text."""
    inlines = as_inlines(*contents, caller="strikethrough")
    return pf.Strikeout(*inlines)


def underline(*contents: Any) -> pf.Underline:
    """Create underlined text."""
    inlines = as_inlines(*contents, caller="underline")
    return pf.Underline(*inlines)


def superscript(*contents: Any) -> pf.Superscript:
    """Create superscript text."""
    inlines = as_inlines(*contents, caller="superscript")
    return pf.Superscript(*inlines)


def subscript(*contents: Any) -> pf.Subscript:
    """Create subscript text."""
    inlines = as_inlines(*contents, caller="subscript")
    return pf.Subscript(*inlines)


def small_caps(*contents: Any) -> pf.SmallCaps:
    """Create small-caps text."""
    inlines = as_inlines(*contents, caller="small_caps")
    return pf.SmallCaps(*inlines)


def code(
    text: str,
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
    language: str | None = None,
) -> pf.Code:
    """Create an inline code snippet."""
    norm_classes = clean_classes(classes)
    if language:
        norm_classes.insert(0, language.lstrip("."))

    return pf.Code(
        text=str(text),
        identifier=clean_identifier(identifier),
        classes=norm_classes,
        attributes=clean_attributes(attributes),
    )


def math(
    text: Any,
    display: bool = False,
    label: str | None = None,
) -> pf.Math | pf.Para:
    """Create mathematical markup.

    Parameters
    ----------
    text : Any
        LaTeX math string or pyndoc Token expression.
    display : bool, default=False
        If True, renders as display math ($$...$$) wrapped in a paragraph;
        otherwise inline math ($...$).
    label : str, optional
        Equation label for cross-referencing (e.g. 'eq:euler').
    """

    math_text = str(text)
    fmt = "DisplayMath" if display else "InlineMath"
    el = pf.Math(text=math_text, format=fmt)

    if display:
        if label:
            norm_label = label if label.startswith("#") else f"#{label}"
            if not norm_label.startswith("#eq:"):
                norm_label = f"#eq:{norm_label.lstrip('#')}"
            return pf.Para(el, pf.Space(), pf.Str("{" + norm_label + "}"))
        return pf.Para(el)

    return el


def inline_math(text: Any) -> pf.Math:
    """Create inline mathematics ($...$)."""
    result = math(text, display=False)
    assert isinstance(result, pf.Math)
    return result


def equation(text: Any, label: str | None = None) -> pf.Math | pf.Para:
    """Create a display equation ($$...$$), optionally labeled for cross-referencing."""
    return math(text, display=True, label=label)


def _normalize_url(url: str) -> str:
    """Normalize user-supplied URL to avoid false positives."""
    if not url:
        return ""
    clean = url.strip()
    # Explicit www. prefix without scheme -> prepend https://
    if clean.lower().startswith("www."):
        return f"https://{clean}"
    # Standard email address without mailto:
    if re.match(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", clean) and not clean.lower().startswith("mailto:"):
        return f"mailto:{clean}"
    return clean


def link(
    *contents: Any,
    url: str | None = None,
    title: str = "",
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
) -> pf.Link:
    """Create a hyperlink.

    Parameters
    ----------
    *contents : Any
        Anchor text / inlines. If `url` is omitted, `contents` text is used as URL
        only if it genuinely matches a domain, URI scheme, or email.
    url : str, optional
        Target destination. Supports web URLs, mailto, relative files, and '#anchors'.
    title : str, default=""
        Hover tooltip title.
    """
    inlines = as_inlines(*contents, caller="link")

    if url is None:
        raw_text = "".join(pf.stringify(inl) for inl in inlines).strip()
        # Verify if raw_text is genuinely a URL, anchor, or email, rather than prose text
        has_spaces = bool(re.search(r"\s", raw_text))
        if not has_spaces and (
            "://" in raw_text
            or raw_text.startswith(("#", "/", "./", "../", "mailto:"))
            or raw_text.lower().startswith("www.")
            or ("@" in raw_text and re.match(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", raw_text))
            or re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?$", raw_text)
        ):
            url = _normalize_url(raw_text)
        else:
            url = ""
    else:
        url = _normalize_url(url)

    return pf.Link(
        *inlines,
        url=str(url or ""),
        title=str(title or ""),
        identifier=clean_identifier(identifier),
        classes=clean_classes(classes),
        attributes=clean_attributes(attributes),
    )


def image(
    url: str,
    *description: Any,
    title: str = "",
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
) -> pf.Image:
    """Create an inline image."""
    inlines = as_inlines(*description, caller="image") if description else []
    return pf.Image(
        *inlines,
        url=str(url),
        title=str(title or ""),
        identifier=clean_identifier(identifier),
        classes=clean_classes(classes),
        attributes=clean_attributes(attributes),
    )


def footnote(*contents: Any) -> pf.Note:
    """Create a footnote note containing the specified inline content."""
    inlines = as_inlines(*contents, caller="footnote")
    return pf.Note(pf.Plain(*inlines))


def citation(
    citation_id: str,
    mode: str = "NormalCitation",
    prefix: Any = None,
    suffix: Any = None,
    note_num: int = 0,
    hash_value: int = 0,
    **kwargs: Any,
) -> pf.Citation:
    """Create a citation item for use inside `cite`."""
    cid = kwargs.pop("id", citation_id)
    h_val = kwargs.pop("hash", hash_value)
    norm_prefix = as_inlines(prefix, caller="citation") if prefix else []
    norm_suffix = as_inlines(suffix, caller="citation") if suffix else []
    return pf.Citation(
        id=clean_identifier(cid),
        mode=str(mode),
        prefix=norm_prefix,
        suffix=norm_suffix,
        note_num=note_num,
        hash=h_val,
    )


def cite(
    contents: Any = None,
    citations: Sequence[pf.Citation | str] | pf.Citation | str | None = None,
) -> pf.Cite:
    """Create a citation block wrapping contents."""
    if citations is None and contents is not None:
        if isinstance(contents, pf.Citation):
            citations = [contents]
            contents = []
        elif (
            isinstance(contents, (list, tuple))
            and contents
            and all(isinstance(c, pf.Citation) for c in contents)
        ):
            citations = contents
            contents = []

    inlines = as_inlines(contents, caller="cite") if contents else []
    citelist: list[pf.Citation] = []

    if citations is not None:
        raw_citations = [citations] if isinstance(citations, (pf.Citation, str)) else citations
        for raw_citation in raw_citations:
            if isinstance(raw_citation, pf.Citation):
                citelist.append(raw_citation)
            else:
                citelist.append(citation(str(raw_citation)))

    return pf.Cite(*inlines, citations=citelist)


def span(
    *contents: Any,
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
) -> pf.Span:
    """Create a Span inline container with attributes and CSS classes."""
    inlines = as_inlines(*contents, caller="span")
    return pf.Span(
        *inlines,
        identifier=clean_identifier(identifier),
        classes=clean_classes(classes),
        attributes=clean_attributes(attributes),
    )
