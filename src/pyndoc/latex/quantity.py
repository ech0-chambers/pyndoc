"""Quantity and Variable representations with Pint integration."""

import copy
from collections.abc import Sequence
from typing import Any

import pint

from .containers import _Container
from .core import (
    CallableToken,
    DimensionedLiteral,
    Literal,
    Token,
    _BinaryOperator,
    _UnaryOperator,
    register_token_converter,
)
from .functions import (
    Exponential,
    Function,
    Logarithm,
    NthRoot,
    _TrigFunction,
)
from .units import format_value, parse_unit, ureg


class Quantity(CallableToken):
    r"""A quantity with a value and unit.

    Parameters
    ----------
    value : float | int | complex | pint.Quantity
        The value of the quantity.
    fmt : str | None, optional
        Format specifier. If None, default format will be used.
    unit : pint.Unit | str | None, optional
        The unit of the quantity.
    """

    _is_quantity: bool = True

    def __init__(
        self,
        value: float | int | complex | pint.Quantity,
        fmt: str | None = None,
        unit: pint.Unit | str | None = None,
    ) -> None:
        if isinstance(value, bool):
            raise TypeError(
                f"Quantity expects a numeric scalar or pint.Quantity, not a bool ({value!r})."
            )
        if isinstance(value, Token):
            raise TypeError(
                f"Quantity expects a numeric scalar or pint.Quantity, not a Token ({type(value).__name__}). "
                "To create a Quantity from an expression or variable, use expr.as_quantity()."
            )
        self._initial_value = value
        self._initial_unit = unit
        self.fmt = fmt
        self._unit: Any | None = None
        self._value: Any = None

        if self._initial_unit is not None:
            self._unit = parse_unit(self._initial_unit)
            if isinstance(self._initial_value, pint.Quantity):
                try:
                    self._value = self._initial_value.to(self._unit)
                except pint.DimensionalityError:
                    raise ValueError(
                        f"Cannot convert {self._initial_value.units} to {self._unit}"
                    )
            else:
                self._value = ureg.Quantity(self._initial_value, self._unit)
        elif isinstance(self._initial_value, pint.Quantity):
            try:
                preferred = self._initial_value.to_preferred()
                self._unit = preferred.units
                self._value = preferred
            except Exception:
                self._unit = self._initial_value.units
                self._value = self._initial_value
        else:
            self._unit = None
            self._value = self._initial_value

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        if isinstance(value, pint.Quantity):
            self._unit = value.units
            self._value = value
            return
        self._initial_value = value
        if self._unit is not None:
            self._value = ureg.Quantity(value, self._unit)
        else:
            self._value = value

    @property
    def unit(self) -> pint.Unit | None:
        return self._unit

    @unit.setter
    def unit(self, unit: pint.Unit | str | None) -> None:
        if unit is None or unit == "":
            if isinstance(self._value, pint.Quantity):
                self._value = self._value.magnitude
            self._unit = None
            return
        parsed_unit = parse_unit(unit)
        if self._unit is None:
            self._unit = parsed_unit
            self._value = ureg.Quantity(self._value, self._unit)
            return
        try:
            self._value = self._value.to(parsed_unit)
            self._unit = self._value.units
        except pint.DimensionalityError:
            raise ValueError(f"Cannot convert {self._unit} to {unit}")

    @property
    def fmt(self) -> str | None:
        return self._fmt

    @fmt.setter
    def fmt(self, fmt: str | None) -> None:
        self._fmt = fmt

    def __call__(
        self, fmt: str | None = None, unit: pint.Unit | str | None = None
    ) -> Literal:
        r"""Returns a Token representing the quantity, formatted as specified."""
        if fmt is None:
            fmt = self.fmt
        if unit is None:
            unit = self._unit
        print_value, has_units = format_value(self.value, fmt, unit)
        if has_units:
            return DimensionedLiteral(print_value)
        return Literal(print_value)

    def __str__(self) -> str:
        return self.__call__().__str__()

    def __float__(self) -> float:
        value = self.value
        if isinstance(value, pint.Quantity):
            return float(value.magnitude)
        return float(self.value)

    def __int__(self) -> int:
        value = self.value
        if isinstance(value, pint.Quantity):
            return int(value.magnitude)
        return int(self.value)


class Variable(CallableToken):
    r"""A variable with a name, value, and optional unit and format specifier.

    Parameters
    ----------
    name : str
        The variable name or symbol representation.
    value : float | int | complex | pint.Quantity | Token
        The value or expression of the variable.
    fmt : str | None, optional
        Format specifier for string representation.
    unit : pint.Unit | str | None, optional
        The unit of the variable.
    """

    _is_symbolic_variable: bool = True

    def __init__(
        self,
        name: str,
        value: float | int | complex | pint.Quantity | Token,
        fmt: str | None = None,
        unit: pint.Unit | str | None = None,
        expandable: bool = True,
    ) -> None:
        self.name = Literal(name)
        if isinstance(value, bool):
            raise TypeError(
                f"Quantity expects a numeric scalar or pint.Quantity, not a bool ({value!r})."
            )
        self._expression: Token | None = value if isinstance(value, Token) else None
        self._expandable: bool = bool(expandable)
        val_for_qty: Any = value
        if isinstance(val_for_qty, Token):
            val_for_qty = getattr(val_for_qty, "value", val_for_qty)
        self._quantity = Quantity(val_for_qty, fmt=fmt, unit=unit)

    def __str__(self) -> str:
        return str(self.name)

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        return self._quantity(*args, **kwargs)

    @property
    def value(self) -> Any:
        return self._quantity.value

    @value.setter
    def value(self, val: Any) -> None:
        if isinstance(val, Token):
            self._expression = val
            val = getattr(val, "value", val)
        else:
            self._expression = None
        self._quantity.value = val

    @property
    def expression(self) -> Token | None:
        """The defining AST expression of this variable, or None if atomic."""
        return self._expression

    @property
    def has_expression(self) -> bool:
        """Whether this variable was defined with an AST expression."""
        return self._expression is not None

    @property
    def expandable(self) -> bool:
        """Whether this variable can be expanded into its expression."""
        return self._expandable

    @expandable.setter
    def expandable(self, value: bool) -> None:
        self._expandable = bool(value)

    def expand_to(
        self,
        depth: int | None = 1,
        no_expand: Sequence[Variable] | Variable | None = None,
    ) -> "ExpandedToken":
        """Expand the variable's expression up to the specified depth.

        Parameters
        ----------
        depth : int | None, default 1
            The maximum expansion depth (>= 1). Depth 1 expands only this variable's
            immediate expression, keeping child variables symbolic. Depth 2 expands
            child variables one level further. If None, expands indefinitely.
        no_expand : Sequence[Variable] | Variable | None, optional
            Variable instances that should not be expanded when encountered in child
            expressions, regardless of their expandable property.

        Returns
        -------
        ExpandedToken
            An AST token representing the expanded expression. The token is callable,
            allowing numeric evaluation and substitution via ``var.expand_to(depth)()``.
        """
        if self._expression is None:
            raise ValueError(
                f"Variable '{self.name}' was not defined with an expression and cannot be expanded."
            )
        if not self._expandable:
            raise ValueError(
                f"Variable '{self.name}' is marked as non-expandable (expandable=False)."
            )
        if depth is not None and depth < 1:
            raise ValueError(f"Expansion depth must be at least 1, got {depth}.")
        if no_expand is not None:
            _normalize_no_expand(no_expand)
        return ExpandedToken(self, depth=depth, no_expand=no_expand)

    @property
    def expand(self) -> "ExpandedToken":
        """Expand the variable's expression by one layer (depth=1)."""
        return self.expand_to(depth=1)

    @property
    def expand_all(self) -> "ExpandedToken":
        """Recursively expand the variable's expression until all variables are atomic."""
        if self._expression is None:
            raise ValueError(
                f"Variable '{self.name}' was not defined with an expression and cannot be expanded."
            )
        if not self._expandable:
            raise ValueError(
                f"Variable '{self.name}' is marked as non-expandable (expandable=False)."
            )
        return ExpandedToken(self, depth=None)

    @property
    def unit(self) -> pint.Unit | None:
        return self._quantity.unit

    @unit.setter
    def unit(self, u: pint.Unit | str) -> None:
        self._quantity.unit = u

    @property
    def fmt(self) -> str | None:
        return self._quantity.fmt

    @fmt.setter
    def fmt(self, f: str | None) -> None:
        self._quantity.fmt = f

    def as_quantity(self) -> Quantity:
        return self._quantity


class ExpandedToken(CallableToken):
    """Represents an expanded AST expression of a Variable."""

    def __init__(
        self,
        variable: Variable,
        depth: int | None = 1,
        no_expand: Sequence[Variable] | Variable | None = None,
    ) -> None:
        if no_expand is not None:
            _normalize_no_expand(no_expand)
        self.variable = variable
        self.depth = depth
        self.no_expand = no_expand

    @property
    def precedence(self) -> int:
        expr = self.variable.expression
        return getattr(expr, "precedence", 100) if expr is not None else 100

    @property
    def value(self) -> Any:
        return self.variable.value

    def __str__(self) -> str:
        expr = self.variable._expression
        if expr is None:
            return str(self.variable)
        next_depth = (self.depth - 1) if self.depth is not None else None
        ast = _substitute_ast(
            expr,
            depth=next_depth,
            evaluate=False,
            visited={id(self.variable)},
            no_expand=self.no_expand,
        )
        return str(ast)

    def __call__(
        self,
        *args: Any,
        no_expand: Sequence[Variable] | Variable | None = None,
        **kwargs: Any,
    ) -> Token:
        expr = self.variable._expression
        effective_no_expand = no_expand or self.no_expand
        if expr is None:
            return self.variable(*args, **kwargs)
        next_depth = (self.depth - 1) if self.depth is not None else None
        ast = _substitute_ast(
            expr,
            depth=next_depth,
            evaluate=True,
            call_args=args,
            call_kwargs=kwargs,
            visited={id(self.variable)},
            no_expand=effective_no_expand,
        )
        return ast


def _normalize_no_expand(
    no_expand: Sequence[Variable] | Variable | None,
) -> set[int]:
    """Extract a set of variable IDs from no_expand."""
    if no_expand is None:
        return set()
    items = no_expand if isinstance(no_expand, (list, tuple, set)) else [no_expand]
    ids: set[int] = set()
    for item in items:
        if isinstance(item, Variable):
            ids.add(id(item))
        else:
            raise TypeError(
                f"no_expand entries must be Variable instances, got {type(item).__name__}."
            )
    return ids


def _substitute_ast(
    token: Any,
    depth: int | None = None,
    evaluate: bool = False,
    call_args: tuple[Any, ...] = (),
    call_kwargs: dict[str, Any] | None = None,
    visited: set[int] | None = None,
    no_expand: Sequence[Variable] | Variable | None = None,
) -> Any:
    """Recursively substitute or evaluate variables in an AST token.

    Parameters
    ----------
    token : Any
        The AST token or literal operand to transform.
    depth : int | None, optional
        Remaining expansion depth for child expressions. If None, expands indefinitely.
    evaluate : bool, default False
        If True, substitutes leaf variables with their evaluated/formatted values.
    call_args : tuple, optional
        Arguments passed to leaf variable calls.
    call_kwargs : dict, optional
        Keyword arguments passed to leaf variable calls (e.g. fmt overrides).
    visited : set of int, optional
        Set of visited Variable object ids for cycle detection.
    no_expand : Sequence[Variable] | Variable | None, optional
        Variables that should not be expanded when encountered.
    """
    if visited is None:
        visited = set()

    no_expand_ids = _normalize_no_expand(no_expand)

    if isinstance(token, Variable):
        if id(token) in visited:
            raise ValueError(
                f"Circular reference detected during variable expansion of '{token.name}'."
            )
        is_in_no_expand = id(token) in no_expand_ids
        is_atomic = not token.has_expression or not token.expandable or is_in_no_expand

        if is_atomic:
            if evaluate:
                return token(*call_args, **(call_kwargs or {}))
            return token

        if evaluate:
            can_descend = depth is None or depth > 0
            if can_descend:
                next_depth = (depth - 1) if depth is not None else None
                return _substitute_ast(
                    token._expression,
                    depth=next_depth,
                    evaluate=True,
                    call_args=call_args,
                    call_kwargs=call_kwargs,
                    visited=visited | {id(token)},
                    no_expand=no_expand,
                )
            return token(*call_args, **(call_kwargs or {}))
        else:
            if depth is not None and depth <= 0:
                return token
            next_depth = (depth - 1) if depth is not None else None
            return _substitute_ast(
                token._expression,
                depth=next_depth,
                evaluate=False,
                visited=visited | {id(token)},
                no_expand=no_expand,
            )

    if isinstance(token, ExpandedToken):
        if evaluate:
            return token(*call_args, no_expand=no_expand, **(call_kwargs or {}))
        return _substitute_ast(
            token.variable._expression,
            depth=token.depth - 1 if token.depth is not None else None,
            evaluate=False,
            visited=visited | {id(token.variable)},
            no_expand=no_expand or token.no_expand,
        )

    if not isinstance(token, Token):
        return token

    new_token = copy.copy(token)

    if isinstance(token, _BinaryOperator):
        new_token.left = _substitute_ast(
            token.left, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        new_token.right = _substitute_ast(
            token.right, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        return new_token

    if isinstance(token, _UnaryOperator):
        new_token.right = _substitute_ast(
            token.right, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        return new_token

    if isinstance(token, _Container):
        new_token.children = [
            _substitute_ast(child, depth, evaluate, call_args, call_kwargs, visited, no_expand)
            for child in token.children
        ]
        return new_token

    if isinstance(token, NthRoot):
        new_token.expr = _substitute_ast(
            token.expr, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        new_token.root = _substitute_ast(
            token.root, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        return new_token

    if isinstance(token, _TrigFunction):
        new_token.expr = _substitute_ast(
            token.expr, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        if token.power is not None:
            new_token.power = _substitute_ast(
                token.power, depth, evaluate, call_args, call_kwargs, visited, no_expand
            )
        return new_token

    if isinstance(token, Logarithm):
        new_token.expr = _substitute_ast(
            token.expr, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        new_token.base = _substitute_ast(
            token.base, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        return new_token

    if isinstance(token, Exponential):
        new_token.expr = _substitute_ast(
            token.expr, depth, evaluate, call_args, call_kwargs, visited, no_expand
        )
        return new_token

    if isinstance(token, Function):
        new_token.args = [
            _substitute_ast(arg, depth, evaluate, call_args, call_kwargs, visited, no_expand)
            for arg in token.args
        ]
        if token.power is not None:
            new_token.power = _substitute_ast(
                token.power, depth, evaluate, call_args, call_kwargs, visited, no_expand
            )
        return new_token

    return new_token


def var(
    name: str,
    value: float | int | complex | pint.Quantity | Token,
    fmt: str | None = None,
    unit: pint.Unit | str | None = None,
    expandable: bool = True,
) -> Variable:
    r"""Create a variable with a name, value, and optional unit, format, and expandable flag."""
    return Variable(name, value, fmt, unit, expandable=expandable)


def _convert_quantity_like(v: Any) -> Quantity:
    if isinstance(v, bool):
        raise TypeError(f"Cannot convert bool '{v}' to Quantity")
    if isinstance(v, pint.Quantity):
        return Quantity(v.magnitude, unit=v.units)
    if isinstance(v, int):
        return Quantity(v, fmt="d")
    return Quantity(v)


register_token_converter((int, float, complex, pint.Quantity), _convert_quantity_like)


__all__ = [
    "ExpandedToken",
    "Quantity",
    "Variable",
    "var",
]

