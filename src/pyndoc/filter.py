#!/usr/bin/env python3
"""Pandoc filter for Pyndoc in-process code execution.

Evaluates inline macros, code blocks, and external Python files directly within
a persistent document-level execution namespace, transforming them into Pandoc AST elements.
"""

from __future__ import annotations

import ast
import contextlib
import io
import logging
import sys
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Any

import panflute

import pyndoc.latex as tex
import pyndoc.markdown as md
from pyndoc.formats import Format
from pyndoc.preprocess import deindent

logger = logging.getLogger("pyndoc.filter")


USER_NAMESPACE: dict[str, Any] = {}


def create_user_namespace() -> dict[str, Any]:
    """Create a fresh execution namespace for document code evaluation.

    Populates standard modules and registers the namespace as the default for
    `tex.symbols`.
    """
    global USER_NAMESPACE
    ns: dict[str, Any] = {
        "__name__": "__main__",
        "__doc__": None,
        "__builtins__": __builtins__,
        "md": md,
        "tex": tex,
        "Format": Format,
        "panflute": panflute,
        "pf": panflute,
    }
    USER_NAMESPACE = ns
    tex.DEFAULT_NAMESPACE = ns
    return ns


# Initialise default execution namespace
create_user_namespace()


def get_raw_format_name(target_format: Format | None) -> str:
    """Map the target format to a format string understood by Panflute RawBlock/RawInline."""
    if target_format is None:
        return "markdown"
    fmt = target_format.name.lower()
    if fmt in ("revealjs", "chunkedhtml"):
        return "html"
    if fmt == "beamer":
        return "latex"
    return fmt


def resolve_target_format(doc: panflute.Doc | None = None) -> Format:
    """Resolve the Pandoc target format from the document, CLI argument, or fallback."""
    raw_fmt: str | None = None
    if doc is not None and getattr(doc, "format", None):
        raw_fmt = doc.format
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        raw_fmt = sys.argv[1]

    if not raw_fmt:
        return Format.MARKDOWN

    raw_fmt_upper = raw_fmt.strip().upper()
    try:
        return Format[raw_fmt_upper]
    except KeyError:
        if raw_fmt.lower() in ("revealjs", "chunkedhtml"):
            return Format.HTML
        if raw_fmt.lower() == "beamer":
            return Format.LATEX
        logger.warning(f"Unrecognised format: {raw_fmt}. Defaulting to MARKDOWN.")
        return Format.MARKDOWN


def handle_file(
    file_path: str, classes: list[str], element_type: type[panflute.Element]
) -> panflute.Element | list:
    """Handle a file element (.py-file). Reads the file and executes it in USER_NAMESPACE."""
    file = Path(file_path)
    # If preprocessor is used, these will have already been caught, but we need
    # to check here anyway in case the preprocessor wasn't used
    if not file.exists():
        return element_type(f"Error: File not found: {file}")
    if not file.is_file():
        return element_type(f"Error: Not a file: {file}")

    try:
        with file.open("r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        return element_type(f"Error reading file {file}: {e}")

    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, USER_NAMESPACE)
    except Exception as e:
        logger.exception(f"Error executing file {file}")
        return element_type(f"Error running file {file}: {e}")

    if "quiet" in classes:
        return []

    out = output_buffer.getvalue()
    out = out.rstrip("\n")

    constructor = (
        panflute.RawBlock if element_type == panflute.CodeBlock else panflute.RawInline
    )
    format_name = get_raw_format_name(md.TARGET_FORMAT)
    return constructor(out, format=format_name)


def _evaluate_element_code(code: str, namespace: dict[str, Any]) -> Any:
    """Evaluate Python code in an element block, allowing preparatory statements followed by an expression."""
    parsed = ast.parse(code)
    if not parsed.body:
        return None
    if isinstance(parsed.body[-1], ast.Expr):
        if len(parsed.body) > 1:
            exec_mod = ast.Module(body=parsed.body[:-1], type_ignores=[])
            exec(compile(exec_mod, "<string>", "exec"), namespace)
        expr = ast.Expression(body=parsed.body[-1].value)
        return eval(compile(expr, "<string>", "eval"), namespace)
    exec(code, namespace)
    return None


def handle_element(
    code: str, classes: list[str], element_type: type[panflute.Element]
) -> panflute.Element | list:
    """Handle an expression element (.py-md). Evaluates code and returns a panflute element."""
    code = deindent(code)
    try:
        result = _evaluate_element_code(code, USER_NAMESPACE)
    except Exception as e:
        logger.exception("Error evaluating expression element")
        return element_type(f"Error running code: {e}")

    if "quiet" in classes:
        return []

    # If the expression returned a tex.Token (or Quantity/Variable), convert to inline math
    if isinstance(result, tex.Token):
        result = md.inline_math(result)

    # If it's a single-element list containing an element, extract it
    if (
        isinstance(result, Sequence)
        and not isinstance(result, (str, bytes))
        and len(result) == 1
        and isinstance(result[0], panflute.Element)
    ):
        result = result[0]

    # If it's not a panflute element or list, convert to panflute Str/Para
    if not isinstance(result, (panflute.Element, Collection)) or isinstance(result, str):
        str_val = str(result)
        if element_type == panflute.CodeBlock or "block" in classes:
            result = panflute.Para(panflute.Str(str_val))
        else:
            result = panflute.Str(str_val)

    if isinstance(result, panflute.Element):
        # Handle block vs inline conversions based on requested classes or container type
        if "inline" in classes and isinstance(result, panflute.Block):
            result = panflute.Span(*result.content)
        elif "block" in classes and isinstance(result, panflute.Inline):
            result = panflute.Para(result)
        elif isinstance(result, panflute.Block) and element_type == panflute.Code:
            logger.warning(
                f"Expected inline but received a block: \n\tCode: {code}\n\tResult: {panflute.stringify(result)}"
            )
            result = panflute.Span(*result.content)
        elif isinstance(result, panflute.Inline) and element_type == panflute.CodeBlock:
            logger.warning(
                f"Expected block but received an inline: \n\tCode: {code}\n\tResult: {panflute.stringify(result)}"
            )
            result = panflute.Para(result)

    return result


def handle_raw(
    code: str, classes: list[str], element_type: type[panflute.Element]
) -> panflute.Element | list:
    """Handle a raw code element (.py). Executes code in USER_NAMESPACE and captures stdout."""
    code = deindent(code)
    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, USER_NAMESPACE)
    except Exception as e:
        logger.exception(f"Error executing raw code block:\n{code}")
        return element_type(f"Error running code: {e}")

    if "quiet" in classes:
        return []

    out = output_buffer.getvalue()
    if out.endswith("\n"):
        out = out[:-1]

    constructor = (
        panflute.RawBlock if element_type == panflute.CodeBlock else panflute.RawInline
    )
    format_name = get_raw_format_name(md.TARGET_FORMAT)
    return constructor(out, format=format_name)


def process_code(elem: panflute.Element) -> panflute.Element | list:
    """Process a code element, determining the type of code block and handling it appropriately."""
    if "py-file" in elem.classes:
        return handle_file(elem.text.strip(), elem.classes, elem.__class__)
    elif "py-md" in elem.classes:
        return handle_element(elem.text.strip(), elem.classes, elem.__class__)
    elif "py" in elem.classes:
        return handle_raw(elem.text.strip(), elem.classes, elem.__class__)
    return elem


def filter(
    elem: panflute.Element, doc: panflute.Doc | None = None
) -> panflute.Element | list | None:
    """Main filter function. Processes each code block in the document."""
    if isinstance(elem, (panflute.CodeBlock, panflute.Code)):
        logger.debug("-" * 40)
        return process_code(elem)
    return None


def prepare(doc: panflute.Doc) -> None:
    """Prepare document state and execution namespace before walking AST."""
    global USER_NAMESPACE
    target_format = resolve_target_format(doc)
    md.TARGET_FORMAT = target_format
    tex.TARGET_FORMAT = target_format
    USER_NAMESPACE = create_user_namespace()
    logger.info(
        f"Initialized in-process execution environment for format: {target_format}"
    )


def run_filter(doc: panflute.Doc | None = None) -> panflute.Doc | None:
    """Run the Pandoc AST filter on the document."""
    return panflute.run_filter(filter, prepare=prepare, doc=doc)


def get_logging() -> None:
    """Check if there is already an active logger, and if not start one."""
    log_file = Path("pyndoc.filters.log")
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            filename=log_file,
            filemode="a",
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            encoding="utf-8",
        )


if __name__ == "__main__":
    get_logging()
    logger.debug("Called filter.py")
    logger.debug("sys.argv: " + str(sys.argv))
    run_filter()
    logger.info("Filter run complete.")
