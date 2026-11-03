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
    "ListType",
    "bullet_list",
    "definition_list",
    "list_item",
    "ordered_list",
    "unordered_list",
]


class ListType(StrEnum):
    """Supported Markdown list container types.

    Attributes
    ----------
    BULLET : "bullet"
        Unordered bullet list (pf.BulletList).
    UNORDERED : "bullet"
        Alias for BULLET.
    ORDERED : "ordered"
        Ordered numbered list (pf.OrderedList).
    DEFINITION : "definition"
        Definition list with term-definition pairs (pf.DefinitionList).
    """

    BULLET = "bullet"
    UNORDERED = "bullet"
    ORDERED = "ordered"
    DEFINITION = "definition"


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


def _resolve_list_type(val: ListType | str) -> ListType:
    if isinstance(val, ListType):
        return val
    clean = str(val).strip().lower()
    for name, member in ListType.__members__.items():
        if clean in (name.lower(), member.value.lower()):
            return member
    raise PanfluteValueError(
        parameter="inner_list_type",
        received=val,
        valid_options=list(dict.fromkeys(name.lower() for name in ListType.__members__)),
        container="list",
    )


def _get_list_constructor(list_type: ListType) -> Any:
    if list_type in (ListType.BULLET, ListType.UNORDERED):
        return bullet_list
    if list_type == ListType.ORDERED:
        return ordered_list
    if list_type == ListType.DEFINITION:
        return definition_list
    raise PanfluteValueError(
        parameter="inner_list_type",
        received=list_type,
        valid_options=list(dict.fromkeys(name.lower() for name in ListType.__members__)),
        container="list",
    )


def _resolve_enumeration(val: Enumeration | str) -> str:
    if isinstance(val, Enumeration):
        return val.value
    clean = str(val).strip().lower()
    for name, member in Enumeration.__members__.items():
        if clean in (name.lower(), member.value.lower()):
            return member.value
    raise PanfluteValueError(
        parameter="enumeration",
        received=val,
        valid_options=list(dict.fromkeys(name.lower() for name in Enumeration.__members__)),
        container="ordered_list",
    )


def _resolve_delimiter(val: ListDelimiter | str) -> str:
    if isinstance(val, ListDelimiter):
        return val.value
    clean = str(val).strip().lower()
    for name, member in ListDelimiter.__members__.items():
        if clean in (name.lower(), member.value.lower()):
            return member.value
    raise PanfluteValueError(
        parameter="delimiter",
        received=val,
        valid_options=list(dict.fromkeys(name.lower() for name in ListDelimiter.__members__)),
        container="ordered_list",
    )


def list_item(
    item: Any,
    inner_list_type: ListType | str | None = None,
) -> pf.ListItem:
    """Create a Panflute ListItem from an element, string, or nested pair.

    Parameters
    ----------
    item : Any
        Text, inline, block, sub-list, or pair `(header, [children])`.
    inner_list_type : ListType | str | None, optional
        The constructor type to use for nested lists. If None, defaults to
        ListType.BULLET when called directly, or inherits the parent list type.
    """
    if isinstance(item, pf.ListItem):
        return item

    if isinstance(item, pf.Block):
        return pf.ListItem(item)

    resolved_inner = (
        _resolve_list_type(inner_list_type)
        if inner_list_type is not None
        else ListType.BULLET
    )

    # Hierarchical pair: (label, subitems)
    if (
        isinstance(item, (tuple, list))
        and len(item) == 2
        and isinstance(item[1], (tuple, list, set))
    ):
        label, children = item
        main_block = as_plain_or_para(label, plain=True, caller="list_item")
        if resolved_inner == ListType.DEFINITION:
            if isinstance(children, Mapping) or (
                isinstance(children, (list, tuple))
                and all(isinstance(x, (tuple, list)) and len(x) == 2 for x in children)
            ):
                constructor = definition_list
            else:
                constructor = bullet_list
        else:
            constructor = _get_list_constructor(resolved_inner)

        sub_list = constructor(children, inner_list_type=inner_list_type)
        return pf.ListItem(main_block, sub_list)

    # Standalone collection passed as an item
    if isinstance(item, (tuple, list, set)):
        if resolved_inner == ListType.DEFINITION:
            if isinstance(item, Mapping) or (
                isinstance(item, (list, tuple))
                and all(isinstance(x, (tuple, list)) and len(x) == 2 for x in item)
            ):
                constructor = definition_list
            else:
                constructor = bullet_list
        else:
            constructor = _get_list_constructor(resolved_inner)

        return pf.ListItem(constructor(item, inner_list_type=inner_list_type))

    # Inlines or strings
    block = as_plain_or_para(item, plain=True, caller="list_item")
    return pf.ListItem(block)


def bullet_list(
    items: Iterable[Any],
    inner_list_type: ListType | str | None = None,
) -> pf.BulletList:
    """Create an unordered bullet list.

    Nested items can be structured as `(parent_text, [children])` pairs.

    Parameters
    ----------
    items : Iterable[Any]
        The sequence of list items or nested pairs.
    inner_list_type : ListType | str | None, optional
        The constructor type to use for nested lists. If None, defaults to
        ListType.BULLET (the same type as this parent list).
    """
    resolved_inner = (
        _resolve_list_type(inner_list_type)
        if inner_list_type is not None
        else ListType.BULLET
    )
    return pf.BulletList(
        *(list_item(item, inner_list_type=resolved_inner) for item in items)
    )


unordered_list = bullet_list


def ordered_list(
    items: Iterable[Any],
    enumeration: Enumeration | str = Enumeration.DEFAULT,
    start: int = 1,
    delimiter: ListDelimiter | str = ListDelimiter.DEFAULT,
    inner_list_type: ListType | str | None = None,
) -> pf.OrderedList:
    """Create an ordered list with custom numbering styles and delimiters.

    Nested items can be structured as `(parent_text, [children])` pairs.

    Parameters
    ----------
    items : Iterable[Any]
        The sequence of list items or nested pairs.
    enumeration : Enumeration | str, default=Enumeration.DEFAULT
        Numbering style (e.g. Decimal, LowerAlpha, LowerRoman).
    start : int, default=1
        Starting number.
    delimiter : ListDelimiter | str, default=ListDelimiter.DEFAULT
        Delimiter style (e.g. Period, OneParen, TwoParens).
    inner_list_type : ListType | str | None, optional
        The constructor type to use for nested lists. If None, defaults to
        ListType.ORDERED (the same type as this parent list).

    Example
    -------

    ````markdown {.example}
    Nested lists inherit their parent list type by default:
    ```{.py-md}
    md.ordered_list(["First item", ("Second item", ["First Subitem", "Second Subitem"]), "Third item"])
    ```
    ````
    """
    style_str = _resolve_enumeration(enumeration)
    delim_str = _resolve_delimiter(delimiter)
    resolved_inner = (
        _resolve_list_type(inner_list_type)
        if inner_list_type is not None
        else ListType.ORDERED
    )

    return pf.OrderedList(
        *(list_item(item, inner_list_type=resolved_inner) for item in items),
        style=style_str,
        start=start,
        delimiter=delim_str,
    )


def definition_list(
    items: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
    inner_list_type: ListType | str | None = None,
) -> pf.DefinitionList:
    """Create a Pandoc DefinitionList from term-definition mappings.

    Parameters
    ----------
    items : Mapping[Any, Any] | Iterable[tuple[Any, Any]]
        Mappings of terms to definitions, or pairs `(term, definitions)`.
    inner_list_type : ListType | str | None, optional
        The constructor type to use for nested lists. If None, defaults to
        ListType.DEFINITION (the same type as this parent list).
    """
    resolved_inner = (
        _resolve_list_type(inner_list_type)
        if inner_list_type is not None
        else ListType.DEFINITION
    )
    entry_dict = items.items() if isinstance(items, Mapping) else items
    def_items: list[pf.DefinitionItem] = []

    for entry in entry_dict:
        if isinstance(entry, (tuple, list)) and len(entry) == 2:
            term, definitions = entry
        else:
            raise PanfluteValueError(
                parameter="items",
                received=entry,
                valid_options=["(term, definitions) pair or Mapping"],
                container="definition_list",
            )

        term_inlines = as_inlines(term, caller="definition_list")

        # Normalize definitions to list of blocks
        if (
            isinstance(definitions, (tuple, list))
            and len(definitions) == 2
            and isinstance(definitions[1], (tuple, list, set))
        ):
            raw_defs = [definitions]
        elif not isinstance(definitions, (list, tuple)):
            raw_defs = [definitions]
        else:
            raw_defs = list(definitions)

        norm_defs: list[pf.Definition] = []
        for d in raw_defs:
            if isinstance(d, pf.Block):
                norm_defs.append(pf.Definition(d))
            elif (
                isinstance(d, (tuple, list))
                and len(d) == 2
                and isinstance(d[1], (tuple, list, set))
            ):
                li = list_item(d, inner_list_type=resolved_inner)
                norm_defs.append(pf.Definition(*li.content))
            elif isinstance(d, (tuple, list, set)):
                if resolved_inner == ListType.DEFINITION:
                    if isinstance(d, Mapping) or (
                        isinstance(d, (list, tuple))
                        and all(isinstance(x, (tuple, list)) and len(x) == 2 for x in d)
                    ):
                        constructor = definition_list
                    else:
                        constructor = bullet_list
                else:
                    constructor = _get_list_constructor(resolved_inner)
                norm_defs.append(pf.Definition(constructor(d, inner_list_type=resolved_inner)))
            else:
                block = as_plain_or_para(d, plain=False, caller="definition_list")
                norm_defs.append(pf.Definition(block))

        def_items.append(pf.DefinitionItem(term=term_inlines, definitions=norm_defs))

    return pf.DefinitionList(*def_items)
