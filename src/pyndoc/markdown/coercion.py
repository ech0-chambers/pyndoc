"""Panflute AST type coercion, validation, and diagnostic error reporting.

This module provides the foundational type coercion and validation layer for
pyndoc's markdown submodule. It normalizes Python primitives, sequences, and
pyndoc LaTeX tokens into strictly valid Panflute AST elements, while producing
helpful, actionable diagnostic error messages when structural AST rules are
violated.
"""

from __future__ import annotations

import difflib
import logging
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import panflute as pf

logger = logging.getLogger("pyndoc.markdown.coercion")

# Global target format placeholder (synchronized with package facade)
TARGET_FORMAT: Any = None

__all__ = [
    "PanfluteError",
    "PanfluteTypeError",
    "PanfluteValueError",
    "as_blocks",
    "as_cells",
    "as_inlines",
    "as_plain_or_para",
    "clean_attributes",
    "clean_classes",
    "clean_identifier",
    "ensure_block",
    "ensure_inline",
    "line_break",
    "math_display",
    "math_inline",
    "para",
    "plain",
    "raw_block",
    "raw_inline",
    "soft_break",
    "space",
    "string",
    "tokenize_text",
]


# ==============================================================================
# Exceptions with Actually Helpful Messages
# ==============================================================================


class PanfluteError(Exception):
    """Base exception for all Panflute AST errors within pyndoc."""


class PanfluteTypeError(PanfluteError, TypeError):
    """Raised when an incompatible element type is supplied to a Panflute wrapper.

    Provides structured diagnostic output explaining what was expected, what was
    received, the underlying AST restriction, and a concrete solution or hint.
    """

    def __init__(
        self,
        expected: str,
        received: Any,
        container: str = "",
        problem: str | None = None,
        solution: str | None = None,
    ) -> None:
        self.expected = expected
        self.received = received
        self.container = container
        self.problem = problem
        self.solution = solution

        recv_type = type(received).__name__
        recv_repr = repr(received)
        if len(recv_repr) > 80:
            recv_repr = recv_repr[:77] + "..."

        context = f"[{container}] " if container else ""
        lines = [
            f"{context}Invalid element type: expected {expected}, but received '{recv_type}' ({recv_repr})."
        ]

        # Attempt to identify the problem, and suggest a solution if possible.
        inferred_problem, inferred_solution = self._infer_diagnostics(
            expected, received, container
        )
        real_problem = problem or inferred_problem
        real_solution = solution or inferred_solution

        if real_problem:
            lines.append(f"  Problem:  {real_problem}")
        if real_solution:
            lines.append(f"  Solution: {real_solution}")

        self.message = "\n".join(lines)
        super().__init__(self.message)

    @staticmethod
    def _infer_diagnostics(
        expected: str, received: Any, container: str
    ) -> tuple[str | None, str | None]:
        """Infer common Panflute AST mistakes and provide potential remediation."""
        caller = container or "wrapper"

        # Case 1: Passing a Block into an Inline container (e.g. md.bold(md.paragraph("x")))
        if isinstance(received, pf.Block):
            problem = (
                f"Panflute does not permit Block elements ('{type(received).__name__}') "
                "to be nested inside Inline elements."
            )
            solution = (
                f"Place the block container on the outside and apply inline styling inside it.\n"
                f"            Example:\n"
                f"                Change: md.{caller}(md.paragraph(...))\n"
                f"                To:     md.paragraph(md.{caller}(...))"
            )
            return problem, solution

        # Case 2: Passing an Inline into a container expecting Block elements
        if isinstance(received, pf.Inline) and "block" in expected.lower():
            problem = (
                f"Container '{caller}' requires Block-level elements (e.g. Para, Plain, Header), "
                f"but received Inline element '{type(received).__name__}'."
            )
            solution = (
                f"Wrap the inline element in a paragraph block first:\n"
                f"            md.paragraph({received!r})"
            )
            return problem, solution

        # Case 3: Passing a dictionary
        if isinstance(received, dict):
            problem = "Dictionaries cannot be directly inserted into AST text containers."
            solution = (
                "If constructing a table, pass the dictionary to 'md.table(dict_data)'.\n"
                "            Otherwise, format key-value pairs into strings or inlines explicitly."
            )
            return problem, solution

        # Generic fallback
        problem = f"Object of type '{type(received).__name__}' cannot be coerced into {expected}."
        solution = "Ensure arguments are strings, numbers, Panflute elements, or LaTeX expressions."
        return problem, solution


class PanfluteValueError(PanfluteError, ValueError):
    """Raised when an invalid configuration value or parameter option is supplied."""

    def __init__(
        self,
        parameter: str,
        received: Any,
        valid_options: Sequence[str] | None = None,
        container: str = "",
        problem: str | None = None,
        solution: str | None = None,
    ) -> None:
        self.parameter = parameter
        self.received = received
        self.valid_options = valid_options
        self.container = container
        self.problem = problem
        self.solution = solution

        context = f"[{container}] " if container else ""
        lines = [f"{context}Invalid value for parameter '{parameter}': {received!r}."]

        if valid_options:
            options_string = ", ".join(repr(o) for o in valid_options)
            lines.append(f"  Valid options are: {options_string}.")

            # Check for close typo matches if received is string-like
            if isinstance(received, str):
                matches = difflib.get_close_matches(
                    received.lower(),
                    [str(o).lower() for o in valid_options],
                    n=1,
                    cutoff=0.5,
                )
                if matches:
                    lines.append(f"  Did you mean: {matches[0]!r}?")

        if problem:
            lines.append(f"  Problem:  {problem}")
        if solution:
            lines.append(f"  Solution: {solution}")
        elif valid_options:
            lines.append("  Solution: Select one of the supported options listed above.")

        self.message = "\n".join(lines)
        super().__init__(self.message)


# ==============================================================================
# Attribute & Identifier Sanitizers
# ==============================================================================


def clean_classes(classes: str | Sequence[str] | None) -> list[str]:
    """Sanitize and normalize CSS/Pandoc class names.

    Strips leading dots and splits whitespace-separated strings. E.g. 
    `".emph .button .confirm-button"` becomes 
    `["emph", "button", "confirm-button"]`
    """
    if classes is None:
        return []
    if isinstance(classes, str):
        raw_list = classes.split()
    elif isinstance(classes, (list, tuple, set)):
        raw_list = []
        for item in classes:
            if isinstance(item, str):
                raw_list.extend(item.split())
            else:
                raw_list.append(str(item))
    else:
        raw_list = [str(classes)]

    return [c.lstrip(".").strip() for c in raw_list if c.lstrip(".").strip()]


def clean_attributes(attributes: Mapping[str, Any] | None) -> dict[str, str]:
    """Normalize HTML/Pandoc element attributes to string key-value mappings."""
    if not attributes:
        return {}
    return {str(k): str(v) for k, v in attributes.items()}


def clean_identifier(identifier: str | None) -> str:
    """Normalize element identifiers by stripping leading anchor hashtags."""
    if not identifier:
        return ""
    return identifier.lstrip("#").strip()


# ==============================================================================
# Text Tokenization & Core Panflute AST Wrappers
# ==============================================================================


def tokenize_text(text: str, soft_breaks: bool = False) -> list[pf.Inline]:
    """Tokenize plain text into strict Pandoc AST inline nodes.

    Splits newlines into `LineBreak` (or `SoftBreak`) and spaces into `Space`
    nodes, ensuring words are cleanly encapsulated in `Str` nodes.

    Parameters
    ----------
    text : str
        The raw text string to tokenize.
    soft_breaks : bool, default=False
        If True, single newlines are converted to `SoftBreak`; otherwise `LineBreak`.

    Returns
    -------
    list[pf.Inline]
        A sequence of valid Panflute Inline elements.
    """
    if not text:
        return []

    lines = text.split("\n")
    all_inlines: list[pf.Inline] = []
    break_factory = pf.SoftBreak if soft_breaks else pf.LineBreak

    for line_idx, line in enumerate(lines):
        if line_idx > 0:
            all_inlines.append(break_factory())

        if not line:
            continue

        # Find alternating non-whitespace words and whitespace chunks
        tokens = re.findall(r"\S+|\s+", line)
        for token in tokens:
            if token.strip() == "":
                # Consecutive whitespace collapses to a single Panflute Space node
                all_inlines.append(pf.Space())
            else:
                all_inlines.append(pf.Str(token))

    return all_inlines


def string(text: str) -> list[pf.Inline]:
    """Convert a plain text string into a list of Panflute Inline elements."""
    return tokenize_text(text)


def space() -> pf.Space:
    """Create a Panflute Space inline element."""
    return pf.Space()


def line_break() -> pf.LineBreak:
    """Create a Panflute LineBreak (hard break) inline element."""
    return pf.LineBreak()


def soft_break() -> pf.SoftBreak:
    """Create a Panflute SoftBreak inline element."""
    return pf.SoftBreak()


def math_inline(text: str) -> pf.Math:
    """Create an inline mathematics element ($...$)."""
    return pf.Math(str(text), format="InlineMath")


def math_display(text: str) -> pf.Math:
    """Create a display mathematics element ($$...$$)."""
    return pf.Math(str(text), format="DisplayMath")


def plain(*contents: Any, caller: str = "plain") -> pf.Plain:
    """Create a Panflute Plain block from arbitrary inline content."""
    inlines = as_inlines(*contents, caller=caller)
    return pf.Plain(*inlines)


def para(*contents: Any, caller: str = "para") -> pf.Para:
    """Create a Panflute Paragraph block from arbitrary inline content."""
    inlines = as_inlines(*contents, caller=caller)
    return pf.Para(*inlines)


def raw_inline(text: str, format: str | None = None) -> pf.RawInline:
    """Create a raw inline markup element in the target format (HTML, LaTeX, etc.)."""
    resolved_format = _resolve_format(format)
    return pf.RawInline(text=str(text), format=resolved_format)


def raw_block(text: str, format: str | None = None) -> pf.RawBlock:
    """Create a raw block markup element in the target format (HTML, LaTeX, etc.)."""
    resolved_format = _resolve_format(format)
    return pf.RawBlock(text=str(text), format=resolved_format)


def _resolve_format(fmt: str | None) -> str:
    """Resolve target document format from parameter or package global state."""
    target: str | None = None

    if fmt is not None:
        target = str(fmt).lower()
    else:
        # Check package facade TARGET_FORMAT
        try:
            import pyndoc.markdown as md

            if md.TARGET_FORMAT is not None:
                target = (
                    md.TARGET_FORMAT.name.lower()
                    if hasattr(md.TARGET_FORMAT, "name")
                    else str(md.TARGET_FORMAT).lower()
                )
        except (ImportError, AttributeError):
            pass

        if target is None and TARGET_FORMAT is not None:
            target = (
                TARGET_FORMAT.name.lower()
                if hasattr(TARGET_FORMAT, "name")
                else str(TARGET_FORMAT).lower()
            )

    if target is None:
        target = "html"

    # Normalize Pandoc HTML variants
    if target in ("revealjs", "chunkedhtml", "s5", "slideous", "slidy", "dzslides"):
        return "html"
    if target in ("beamer",):
        return "latex"
    return target


# ==============================================================================
# Type Coercion & Normalization Engine
# ==============================================================================


def _is_latex_token(obj: Any) -> bool:
    """Check if an object is a pyndoc LaTeX Token without triggering circular imports."""
    try:
        from pyndoc.latex.core import Token

        return isinstance(obj, Token)
    except ImportError:
        return False


def as_inlines(*contents: Any, caller: str = "as_inlines") -> list[pf.Inline]:
    """Coerce arbitrary items into a flat list of Panflute Inline elements.

    Supported inputs:
    - `str`: Tokenized into `Str`, `Space`, and `LineBreak` nodes.
    - `int`, `float`, `complex`: Stringified into atomic `Str` nodes.
    - `pf.Inline`: Appended directly.
    - `pyndoc.latex.Token`: Converted to inline math `pf.Math(str(token), format="InlineMath")`.
    - `Iterable` (list, tuple, generator): Recursively flattened and coerced.
    - `None`: Skipped.

    Raises
    ------
    PanfluteTypeError
        If a `pf.Block` element or unconvertible object is encountered.
    """
    inlines: list[pf.Inline] = []

    for item in contents:
        if item is None:
            continue

        if isinstance(item, pf.Inline):
            inlines.append(item)
        elif isinstance(item, str):
            inlines.extend(string(item))
        elif isinstance(item, (int, float, complex)):
            inlines.append(pf.Str(str(item)))
        elif _is_latex_token(item):
            inlines.append(pf.Math(str(item), format="InlineMath"))
        elif isinstance(item, (list, tuple, set)) or (
            isinstance(item, Iterable) and not isinstance(item, (str, bytes, pf.Element))
        ):
            # Recursively flatten nested iterables
            inlines.extend(as_inlines(*item, caller=caller))
        elif isinstance(item, pf.Block):
            raise PanfluteTypeError(
                container=caller,
                expected="Inline element, string, or number",
                received=item,
            )
        else:
            raise PanfluteTypeError(
                container=caller,
                expected="Inline element, string, or number",
                received=item,
            )

    return inlines


def as_blocks(*contents: Any, caller: str = "as_blocks") -> list[pf.Block]:
    """Coerce arbitrary items into a flat list of Panflute Block elements.

    Consecutive inline elements, strings, numbers, and tokens are automatically
    grouped into `pf.Para` paragraph blocks. Pre-existing `pf.Block` elements are
    preserved.

    If a pyndoc LaTeX `Token` is the sole pending inline when between blocks (or
    standalone), it is rendered as a standalone display math equation
    (`pf.Para(pf.Math(..., format="DisplayMath"))`). If combined with adjacent text
    or other inlines, it renders as inline math within that paragraph.

    Supported inputs:
    - `pf.Block`: Appended directly.
    - `pf.Inline`, `str`, `int`, `float`: Grouped into `pf.Para`.
    - `pyndoc.latex.Token`: Rendered as display math (if standalone) or inline math.
    - `Iterable` (list, tuple): Recursively flattened and coerced.
    - `None`: Skipped.

    Raises
    ------
    PanfluteTypeError
        If an uncoercible object type is encountered.
    """
    blocks: list[pf.Block] = []
    # Track (inline_node, is_token) pairs to identify standalone tokens between blocks
    pending_entries: list[tuple[pf.Inline, bool]] = []

    def flush_pending_inlines() -> None:
        if not pending_entries:
            return
        # If a single Token is the only pending inline, render as DisplayMath
        if len(pending_entries) == 1 and pending_entries[0][1]:
            math_text = pending_entries[0][0].text
            blocks.append(pf.Para(pf.Math(math_text, format="DisplayMath")))
        else:
            inlines = [entry[0] for entry in pending_entries]
            blocks.append(pf.Para(*inlines))
        pending_entries.clear()

    # Flatten top-level contents
    flat_items: list[Any] = []

    def flatten(items: Iterable[Any]) -> None:
        for item in items:
            if item is None:
                continue
            if isinstance(item, (list, tuple, set)) or (
                isinstance(item, Iterable)
                and not isinstance(item, (str, bytes, pf.Element))
            ):
                flatten(item)
            else:
                flat_items.append(item)

    flatten(contents)

    for item in flat_items:
        if isinstance(item, pf.Block):
            flush_pending_inlines()
            blocks.append(item)
        elif isinstance(item, pf.Inline):
            pending_entries.append((item, False))
        elif isinstance(item, str):
            for inl in tokenize_text(item):
                pending_entries.append((inl, False))
        elif isinstance(item, (int, float, complex)):
            pending_entries.append((pf.Str(str(item)), False))
        elif _is_latex_token(item):
            pending_entries.append((pf.Math(str(item), format="InlineMath"), True))
        else:
            raise PanfluteTypeError(
                container=caller,
                expected="Block element, Inline element, string, or number",
                received=item,
            )

    flush_pending_inlines()
    return blocks


def as_plain_or_para(
    content: Any, plain: bool = True, caller: str = "as_plain_or_para"
) -> pf.Plain | pf.Para | pf.Block:
    """Coerce content into a single block container.

    If `content` is already a `pf.Block`, it is returned unchanged. Otherwise,
    inlines and text are wrapped in `pf.Plain` (default) or `pf.Para`.
    """
    if isinstance(content, pf.Block):
        return content

    inlines = as_inlines(content, caller=caller)
    wrapper = pf.Plain if plain else pf.Para
    return wrapper(*inlines)


def as_cells(*contents: Any, caller: str = "as_cells") -> list[pf.TableCell]:
    """Coerce items into a list of Panflute TableCell elements.

    Elements already wrapped as `pf.TableCell` are preserved. Block elements are
    wrapped in `pf.TableCell(block)`. Inlines, strings, and numbers are wrapped
    in `pf.TableCell(pf.Plain(*inlines))`.
    """
    cells: list[pf.TableCell] = []

    # Flatten if a single iterable was passed
    flat_items: list[Any] = []
    if len(contents) == 1 and isinstance(contents[0], (list, tuple)):
        flat_items.extend(contents[0])
    else:
        flat_items.extend(contents)

    for item in flat_items:
        if isinstance(item, pf.TableCell):
            cells.append(item)
        elif isinstance(item, pf.Block):
            cells.append(pf.TableCell(item))
        else:
            cells.append(pf.TableCell(as_plain_or_para(item, plain=True, caller=caller)))

    return cells


def ensure_inline(item: Any, caller: str = "ensure_inline") -> pf.Inline:
    """Ensure a single Panflute Inline element is returned.

    If given multiple inlines or a multi-token string, groups them into a `pf.Span`.
    """
    if isinstance(item, pf.Inline):
        return item
    if isinstance(item, pf.Block):
        raise PanfluteTypeError(
            container=caller,
            expected="Single Inline element or string",
            received=item,
        )

    inlines = as_inlines(item, caller=caller)
    if len(inlines) == 1:
        return inlines[0]
    return pf.Span(*inlines)


def ensure_block(item: Any, caller: str = "ensure_block") -> pf.Block:
    """Ensure a single Panflute Block element is returned."""
    if isinstance(item, pf.Block):
        return item

    blocks = as_blocks(item, caller=caller)
    if len(blocks) == 1:
        return blocks[0]
    return pf.Div(*blocks)
