"""Shorthand assignment DSL parser for mathematical symbols and variables."""

import re
from typing import Optional, Dict, Any, Tuple
from .core import Token, as_token
from .quantity import var


def __pythonify_name(name: str) -> str:
    replacements = [
        (" ", "_"),
        ("-", "_"),
        ("\\", ""),
        ("{", ""),
        ("}", ""),
    ]
    for old, new in replacements:
        name = name.replace(old, new)
    if not name[0].isalpha():
        name = "_" + name
    for c in name:
        if not c.isalnum() and c != "_":
            name = name.replace(c, "")
    return name


__value_pattern = re.compile(
    r"^(?P<value>[\d\.ed\+\-,]+)(?:[^\S\n\r]+(?P<units>[^\(\n]*?)?(?:[^\S\n\r]*\((?P<fmt>.*)\))?)?$"
)

DEFAULT_NAMESPACE: Optional[Dict[str, Any]] = None


def define_symbols(
    statements: str,
    namespace: Optional[Dict[str, Any]] = None,
) -> None | Tuple[Token, ...]:
    """Parse shorthand variable assignment statements into Python/LaTeX symbols."""
    if namespace is None:
        try:
            import pyndoc.latex as _tex
            namespace = getattr(_tex, "DEFAULT_NAMESPACE", None)
        except ImportError:
            namespace = None
        if namespace is None:
            namespace = DEFAULT_NAMESPACE

    statement_list = statements.split("\n")
    statement_list = [stmt.split(";") for stmt in statement_list]
    statement_list = [stmt.strip() for stmts in statement_list for stmt in stmts]
    statement_list = [stmt.split("#")[0].strip() for stmt in statement_list]
    statement_list = [stmt for stmt in statement_list if stmt]

    assignments = []
    for statement in statement_list:
        if "=" not in statement:
            new_name = __pythonify_name(statement)
            if namespace is not None and new_name in namespace:
                raise ValueError(f"Symbol {new_name} already defined")
            new_symbol = as_token(statement)
            if namespace is not None:
                namespace[new_name] = new_symbol
            assignments.append(new_symbol)
            continue
        name, value = statement.split("=")
        name = name.strip()
        value = value.strip()
        if "'" in value or '"' in value:
            raise NotImplementedError("String values are not yet supported")
        matched = __value_pattern.match(value)
        if matched is None:
            raise ValueError(f"Could not parse value `{value}`")
        value = matched.group("value")
        units = matched.group("units")
        fmt = matched.group("fmt")
        new_name = __pythonify_name(name)
        if namespace is not None and new_name in namespace:
            raise ValueError(f"Symbol {new_name} already defined")
        val = float(value)
        if val.is_integer():
            val = int(val)
        new_symbol = var(name, val, unit=units, fmt=fmt)
        if namespace is not None:
            namespace[new_name] = new_symbol
        assignments.append(new_symbol)
    return tuple(assignments)


symbols = define_symbols

__all__ = [
    "DEFAULT_NAMESPACE",
    "define_symbols",
    "symbols",
]
