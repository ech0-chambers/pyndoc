"""Shorthand assignment DSL parser for mathematical symbols and variables."""
import re
import sys
from typing import Any, Dict, Optional, Tuple
from pyndoc.latex.core import Token, as_token
from pyndoc.latex.quantity import var

VALUE_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) # Int, float, or scientific notation
    (?:\s+(?P<units>[^\(;]+?))?                             # Optional physical unit string
    (?:\s*\((?P<fmt>[^\)]+)\))?                             # Optional format specifier: (.3f)
    \s*$
    """,
    re.VERBOSE,
)

DEFAULT_NAMESPACE: Optional[Dict[str, Any]] = None


def pythonify_name(name: str) -> str:
    """Convert a LaTeX symbol name into a valid, safe Python identifier.

    Examples
    --------
    >>> pythonify_name(r"\\alpha_{i}")
    'alpha_i'
    >>> pythonify_name(r"\\Delta T")
    'Delta_T'
    >>> pythonify_name("x'")
    'x_prime'
    """
    name = name.strip()
    replacements = [
        (" ", "_"),
        ("-", "_"),
        ("'", "_prime"),
        ("\\", ""),
        ("{", ""),
        ("}", ""),
    ]
    for old, new in replacements:
        name = name.replace(old, new)

    cleaned = "".join(c for c in name if c.isalnum() or c == "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")

    if not cleaned:
        return "_sym"
    if not cleaned[0].isalpha() and cleaned[0] != "_":
        cleaned = "_" + cleaned
    return cleaned


def define_symbols(
    statements: str,
    namespace: Optional[Dict[str, Any]] = None,
    allow_redefinition: bool = False,
) -> Tuple[Token, ...]:
    """Parse shorthand symbol declaration statements into Variable or Token objects.

    Parameters
    ----------
    statements : str
        Newline- or semicolon-delimited variable declarations, e.g.:
        "a = 5 m; b = 10 s; \\alpha_{i} = 4 (.2f); p_i;"
    namespace : Optional[Dict[str, Any]]
        Target dictionary to populate with the parsed variables. If None,
        resolves dynamically to pyndoc.latex.DEFAULT_NAMESPACE.
    allow_redefinition : bool, default False
        Whether to overwrite existing variables in the namespace. If False,
        raises a ValueError when an existing name is encountered.

    Returns
    -------
    Tuple[Token, ...]
        Tuple of constructed Token or Variable instances.
    """
    # Get the parent module namespace if it's available.
    # If not, use this module's namespace
    # If that's also None, we'll just return definitions, not assign them
    if namespace is None:
        latex_mod = sys.modules.get("pyndoc.latex")
        if latex_mod is not None:
            namespace = getattr(latex_mod, "DEFAULT_NAMESPACE", None)
        if namespace is None:
            namespace = DEFAULT_NAMESPACE

    # Phase 1: Strip line comments BEFORE splitting on semicolons
    raw_statements = []
    for line in statements.splitlines():
        line_clean = line.split("#", 1)[0].strip()
        if not line_clean:
            continue
        for part in line_clean.split(";"):
            statement = part.strip()
            if statement:
                raw_statements.append(statement)

    # Phase 2: Partition each statement into name and optional value definition
    assignments: list[Token] = []
    for statement in raw_statements:
        raw_name, sep, raw_value = statement.partition("=")
        raw_name = raw_name.strip()
        raw_value = raw_value.strip()

        if not raw_name:
            raise ValueError(f"Empty variable name in statement: '{statement}'")

        py_name = pythonify_name(raw_name)

        if namespace is not None and not allow_redefinition and py_name in namespace:
            raise ValueError(f"Symbol '{py_name}' already defined in namespace")

        if not sep:
            # Bare symbol declaration without an assigned value: e.g. "p_i;" or "\alpha;"
            symbol_obj = as_token(raw_name)
        else:
            # Value assignment: e.g. "m = 5 kg (.2f)" or "c = 3.4e-3 m/s"
            match = VALUE_PATTERN.match(raw_value)
            if not match:
                raise ValueError(
                    f"Could not parse value, unit, or format in assignment: '{statement}'"
                )

            val_str = match.group("value")
            units = match.group("units")
            fmt = match.group("fmt")

            val_num: int | float = float(val_str)
            if val_num.is_integer():
                val_num = int(val_num)

            clean_units = units.strip() if units else None
            clean_fmt = fmt.strip() if fmt else None

            symbol_obj = var(raw_name, val_num, unit=clean_units, fmt=clean_fmt)

        if namespace is not None:
            namespace[py_name] = symbol_obj

        assignments.append(symbol_obj)

    return tuple(assignments)


symbols = define_symbols


__all__ = [
    "DEFAULT_NAMESPACE",
    "define_symbols",
    "symbols",
]
