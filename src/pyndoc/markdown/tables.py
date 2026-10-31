"""Panflute Table AST constructors with multi-format data ingestion and alignment inference.

This module provides high-level table creation helpers (`table`, `table_row`,
`table_cell`) that normalize 2D sequences, column mappings, NumPy arrays, and
Pandas DataFrames into valid Pandoc AST Table elements.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

import panflute as pf

from pyndoc.markdown.coercion import (
    PanfluteTypeError,
    PanfluteValueError,
    as_cells,
    as_inlines,
    as_plain_or_para,
    clean_attributes,
    clean_classes,
    clean_identifier,
)

logger = logging.getLogger("pyndoc.markdown.tables")

__all__ = [
    "Alignment",
    "table",
    "table_body",
    "table_cell",
    "table_foot",
    "table_head",
    "table_row",
]


class Alignment(StrEnum):
    """Column alignment styles for Pandoc tables."""

    LEFT = "AlignLeft"
    CENTER = "AlignCenter"
    CENTRE = "AlignCenter"
    RIGHT = "AlignRight"
    DEFAULT = "AlignDefault"


def resolve_alignment(align: Alignment | str | None) -> Alignment:
    """Resolve an alignment from an Alignment enum or string."""
    if align is None:
        return Alignment.DEFAULT
    if isinstance(align, Alignment):
        return align

    key = str(align).strip().lower()
    for member in Alignment:
        if key in (member.name.lower(), member.value.lower(), member.value[5:].lower()):
            return member

    raise PanfluteValueError(
        parameter="alignment",
        received=align,
        valid_options=["left", "center", "right", "default"],
        container="table",
    )


def table_cell(
    content: Any,
    alignment: Alignment | str | None = None,
    row_span: int = 1,
    col_span: int = 1,
    rowspan: int | None = None,
    colspan: int | None = None,
) -> pf.TableCell:
    """Create a single TableCell containing blocks or coerced inlines."""
    if isinstance(content, pf.TableCell):
        return content

    norm_block = as_plain_or_para(content, plain=True, caller="table_cell")

    align_str = None
    if alignment:
        align_str = resolve_alignment(alignment).value

    final_rowspan = rowspan if rowspan is not None else row_span
    final_colspan = colspan if colspan is not None else col_span

    kwargs: dict[str, Any] = {"rowspan": final_rowspan, "colspan": final_colspan}
    if align_str:
        kwargs["alignment"] = align_str

    return pf.TableCell(norm_block, **kwargs)


def table_row(*cells: Any) -> pf.TableRow:
    """Create a TableRow containing table cells."""
    norm_cells = as_cells(*cells, caller="table_row")
    return pf.TableRow(*norm_cells)


def table_head(*rows: Any) -> pf.TableHead:
    """Create a TableHead containing header rows."""
    norm_rows: list[pf.TableRow] = []
    flat_rows = rows[0] if len(rows) == 1 and isinstance(rows[0], (list, tuple)) else rows
    for r in flat_rows:
        if isinstance(r, pf.TableRow):
            norm_rows.append(r)
        else:
            norm_rows.append(table_row(r))
    return pf.TableHead(*norm_rows)


def table_body(*rows: Any) -> pf.TableBody:
    """Create a TableBody containing body rows."""
    norm_rows: list[pf.TableRow] = []
    flat_rows = rows[0] if len(rows) == 1 and isinstance(rows[0], (list, tuple)) else rows
    for r in flat_rows:
        if isinstance(r, pf.TableRow):
            norm_rows.append(r)
        else:
            norm_rows.append(table_row(r))
    return pf.TableBody(*norm_rows)


def table_foot(*rows: Any) -> pf.TableFoot:
    """Create a TableFoot containing footer rows."""
    norm_rows: list[pf.TableRow] = []
    flat_rows = rows[0] if len(rows) == 1 and isinstance(rows[0], (list, tuple)) else rows
    for r in flat_rows:
        if isinstance(r, pf.TableRow):
            norm_rows.append(r)
        else:
            norm_rows.append(table_row(r))
    return pf.TableFoot(*norm_rows)


def table(
    data: Any,
    headers: Sequence[Any] | None = None,
    alignments: Sequence[str] | str | None = None,
    widths: Sequence[float] | float | None = None,
    caption: Any = None,
    identifier: str | None = None,
    classes: list[str] | str | None = None,
    attributes: dict[str, Any] | None = None,
) -> pf.Table:
    """Construct a high-level Panflute Table from multi-format data.

    Parameters
    ----------
    data : Sequence[Sequence[Any]] | Mapping[str, Sequence[Any]] | Any
        Input table data (2D list, dictionary of columns, NumPy array, or DataFrame).
    headers : Sequence[Any], optional
        List of header cell values. Derived automatically if `data` is a mapping/DataFrame.
    alignments : Sequence[str] | str, optional
        Column alignments ('left', 'center', 'right', 'default'). Numbers auto-default
        to 'right', text to 'left'.
    widths : Sequence[float] | float, optional
        Fractional column widths (0.0 to 1.0) or 'ColWidthDefault'.
    caption : Any, optional
        Table caption text or inline elements.
    """
    rows_data, derived_headers = _extract_table_data(data)
    final_headers = headers if headers is not None else derived_headers

    num_cols = 0
    if final_headers:
        num_cols = len(final_headers)
    elif rows_data:
        num_cols = max(len(r) for r in rows_data)

    if num_cols == 0:
        raise PanfluteValueError(
            parameter="data",
            received=data,
            container="table",
            problem="Table data has 0 columns.",
            solution="Provide at least one row or column of data.",
        )

    # Resolve column alignments
    col_alignments = _resolve_alignments(alignments, num_cols, rows_data)

    # Resolve column widths
    col_widths = _resolve_widths(widths, num_cols)

    colspec = list(zip(col_alignments, col_widths))

    # Build Header
    head_element = None
    if final_headers:
        header_cells = [table_cell(h, alignment=col_alignments[i]) for i, h in enumerate(final_headers)]
        head_element = pf.TableHead(pf.TableRow(*header_cells))

    # Build Body
    body_rows: list[pf.TableRow] = []
    for row in rows_data:
        row_cells = [
            table_cell(cell, alignment=col_alignments[i] if i < len(col_alignments) else None)
            for i, cell in enumerate(row)
        ]
        body_rows.append(pf.TableRow(*row_cells))

    body_element = pf.TableBody(*body_rows)

    # Build Caption
    caption_element = None
    if caption:
        if isinstance(caption, pf.Caption):
            caption_element = caption
        else:
            cap_inlines = as_inlines(caption, caller="table")
            caption_element = pf.Caption(pf.Plain(*cap_inlines))

    return pf.Table(
        body_element,
        head=head_element,
        colspec=colspec,
        caption=caption_element,
        identifier=clean_identifier(identifier),
        classes=clean_classes(classes),
        attributes=clean_attributes(attributes),
    )


def _extract_table_data(data: Any) -> tuple[list[list[Any]], list[Any] | None]:
    """Extract rows and optional headers from diverse Python data structures."""
    # Case 1: Pandas DataFrame (duck-typed)
    if hasattr(data, "columns") and hasattr(data, "itertuples"):
        headers = list(data.columns)
        rows = [list(row)[1:] for row in data.itertuples()]  # skip index
        return rows, headers

    # Case 2: Mapping of columns: {'Col1': [1, 2], 'Col2': [3, 4]}
    if isinstance(data, Mapping):
        headers = list(data.keys())
        col_values = [list(data[k]) for k in headers]
        max_rows = max((len(c) for c in col_values), default=0)
        rows = []
        for r_idx in range(max_rows):
            row = [col[r_idx] if r_idx < len(col) else "" for col in col_values]
            rows.append(row)
        return rows, headers

    # Case 3: 2D Sequences or NumPy array
    if hasattr(data, "tolist"):  # NumPy ndarray
        data = data.tolist()

    if isinstance(data, (list, tuple)):
        rows = []
        for r in data:
            if isinstance(r, (list, tuple)):
                rows.append(list(r))
            else:
                rows.append([r])
        return rows, None

    raise PanfluteTypeError(
        expected="2D Sequence, Mapping, NumPy array, or DataFrame",
        received=data,
        container="table",
        problem=f"Unsupported table data structure '{type(data).__name__}'.",
        solution="Pass a 2D list (e.g. [['A', 1], ['B', 2]]) or dictionary of columns.",
    )


def _resolve_alignments(
    alignments: Sequence[Alignment | str] | Alignment | str | None,
    num_cols: int,
    rows: list[list[Any]],
) -> list[str]:
    """Resolve column alignments with sensible defaults."""
    if alignments is None:
        # Infer: numeric columns right-aligned, text left-aligned
        inferred = []
        for col_idx in range(num_cols):
            numeric_count = 0
            total_count = 0
            for r in rows:
                if col_idx < len(r):
                    val = r[col_idx]
                    total_count += 1
                    if isinstance(val, (int, float, complex)):
                        numeric_count += 1
            if total_count > 0 and numeric_count / total_count >= 0.7:
                inferred.append(Alignment.RIGHT.value)
            else:
                inferred.append(Alignment.DEFAULT.value)
        return inferred

    if isinstance(alignments, (Alignment, str)):
        align_str = resolve_alignment(alignments).value
        return [align_str] * num_cols

    result = []
    for a in alignments:
        result.append(resolve_alignment(a).value)

    while len(result) < num_cols:
        result.append(Alignment.DEFAULT.value)
    return result[:num_cols]


def _resolve_widths(widths: Sequence[float] | float | None, num_cols: int) -> list[Any]:
    """Resolve Pandoc column width specifications."""
    if widths is None or widths == "auto":
        return ["ColWidthDefault"] * num_cols

    if isinstance(widths, (int, float)):
        return [float(widths)] * num_cols

    result: list[float | str] = []
    for w in widths:
        if w is None or w == "auto" or w == "ColWidthDefault":
            result.append("ColWidthDefault")
        else:
            result.append(float(w))

    while len(result) < num_cols:
        result.append("ColWidthDefault")
    return result[:num_cols]
