"""Panflute List AST constructors with hierarchical recursion and validation.

This module provides wrappers for BulletList, OrderedList, ListItem, and
DefinitionList. It supports clean recursive tree hierarchies.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Any

import panflute as pf

from pyndoc.markdown.coercion import (
    PanfluteValueError,
    as_inlines,
    as_plain_or_para,
)

logger = logging.getLogger("pyndoc.markdown.lists")

__all__ = [
    "Enumeration",
    "ListDelimiter",
    "bullet_list",
    "definition_list",
    "list_item",
    "ordered_list",
    "unordered_list",
]


class Enumeration(StrEnum):
    """Enumeration numbering styles for ordered lists."""

    DECIMAL = "Decimal"
    ARABIC = "Decimal"
    LOWER_ALPHA = "LowerAlpha"
    ALPH_LOWER = "LowerAlpha"
    UPPER_ALPHA = "UpperAlpha"
    ALPH_UPPER = "UpperAlpha"
    LOWER_ROMAN = "LowerRoman"
    ROMAN_LOWER = "LowerRoman"
    UPPER_ROMAN = "UpperRoman"
    ROMAN_UPPER = "UpperRoman"
    EXAMPLE = "Example"
    DEFAULT = "DefaultStyle"


class ListDelimiter(StrEnum):
    """Delimiter punctuation for ordered list markers."""

    PERIOD = "Period"
    ONE_PAREN = "OneParen"
    TWO_PAREN = "TwoParens"
    TWO_PARENS = "TwoParens"
    DEFAULT = "DefaultDelim"


def _resolve_enumeration(val: Enumeration | str) -> str:
    if isinstance(val, Enumeration):
        return val.value
    clean = str(val).strip()
    for member in Enumeration:
        if clean.lower() in (member.name.lower(), member.value.lower()):
            return member.value
    raise PanfluteValueError(
        parameter="enumeration",
        received=val,
        valid_options=[e.name.lower() for e in Enumeration],
        container="ordered_list",
    )


def _resolve_delimiter(val: ListDelimiter | str) -> str:
    if isinstance(val, ListDelimiter):
        return val.value
    clean = str(val).strip()
    for member in ListDelimiter:
        if clean.lower() in (member.name.lower(), member.value.lower()):
            return member.value
    raise PanfluteValueError(
        parameter="delimiter",
        received=val,
        valid_options=[d.name.lower() for d in ListDelimiter],
        container="ordered_list",
    )


def list_item(item: Any) -> pf.ListItem:
    """Create a Panflute ListItem from an element, string, or nested pair.

    Parameters
    ----------
    item : Any
        Text, inline, block, sub-list, or pair `(header, [children])`.
    """
    if isinstance(item, pf.ListItem):
        return item

    if isinstance(item, pf.Block):
        return pf.ListItem(item)

    # Hierarchical pair: (label, subitems)
    if (
        isinstance(item, (tuple, list))
        and len(item) == 2
        and isinstance(item[1], (tuple, list, set))
    ):
        label, children = item
        main_block = as_plain_or_para(label, plain=True, caller="list_item")
        sub_list = bullet_list(children)
        return pf.ListItem(main_block, sub_list)

    # Standalone collection passed as an item
    if isinstance(item, (tuple, list, set)):
        return pf.ListItem(bullet_list(item))

    # Inlines or strings
    block = as_plain_or_para(item, plain=True, caller="list_item")
    return pf.ListItem(block)


def bullet_list(items: Iterable[Any]) -> pf.BulletList:
    """Create an unordered bullet list.

    Nested items can be structured as `(parent_text, [children])` pairs.
    """
    return pf.BulletList(*(list_item(item) for item in items))


unordered_list = bullet_list


def ordered_list(
    items: Iterable[Any],
    enumeration: Enumeration | str = Enumeration.DEFAULT,
    start: int = 1,
    delimiter: ListDelimiter | str = ListDelimiter.DEFAULT,
) -> pf.OrderedList:
    """Create an ordered list with custom numbering styles and delimiters.

    Nested items can be structured as `(parent_text, [children])` pairs.
    """
    style_str = _resolve_enumeration(enumeration)
    delim_str = _resolve_delimiter(delimiter)

    return pf.OrderedList(
        *(list_item(item) for item in items),
        style=style_str,
        start=start,
        delimiter=delim_str,
    )


def definition_list(items: Mapping[Any, Any] | Iterable[tuple[Any, Any]]) -> pf.DefinitionList:
    """Create a Pandoc DefinitionList from term-definition mappings."""
    entry_dict = items.items() if isinstance(items, Mapping) else items
    def_items: list[pf.DefinitionItem] = []

    for term, definitions in entry_dict:
        term_inlines = as_inlines(term, caller="definition_list")

        # Normalize definitions to list of blocks
        raw_defs = [definitions] if not isinstance(definitions, (list, tuple)) else definitions
        norm_defs: list[pf.Definition] = []
        for d in raw_defs:
            block = as_plain_or_para(d, plain=False, caller="definition_list")
            norm_defs.append(pf.Definition(block))

        def_items.append(pf.DefinitionItem(term=term_inlines, definitions=norm_defs))

    return pf.DefinitionList(*def_items)
