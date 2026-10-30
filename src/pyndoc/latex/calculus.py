"""Calculus expressions: integrals, derivatives, limits, and summations."""

from typing import Any, Optional
from .core import Token, Macro, Literal, as_token
from .containers import Collection


class Tends(Token):
    def __init__(self, variable: Token | Any, limit: Token | Any) -> None:
        """A limit expression, such as `x \\to a`."""
        self.variable = as_token(variable)
        self.limit = as_token(limit)

    def __str__(self) -> str:
        return f"{self.variable} \\to {self.limit}"


class LimitsExpression(Token):
    def __init__(
        self,
        function: Macro | Token | str,
        expr: Token | Any,
        lower: Token | Any = None,
        upper: Token | Any = None,
        suffix: Token | Any = None,
    ):
        """A mathematical expression with limits, such as an integral or summation."""
        self.value = None
        if isinstance(function, str):
            function = Macro(function)
        self.function = function
        self.lower = None if lower is None else as_token(lower)
        self.upper = None if upper is None else as_token(upper)
        self.expr = as_token(expr)
        self.suffix = None if suffix is None else as_token(suffix)

    def __str__(self) -> str:
        suffix = "" if self.suffix is None else str(self.suffix)
        if self.lower is None and self.upper is None:
            return f"{self.function} {self.expr} {suffix}"
        if self.lower is None:
            return f"{self.function} \\limits ^{{{self.upper}}} {self.expr} {suffix}"
        if self.upper is None:
            return f"{self.function} \\limits _{{{self.lower}}} {self.expr} {suffix}"
        return f"{self.function} \\limits _{{{self.lower}}} ^{{{self.upper}}} {self.expr} {suffix}"


class Integral(LimitsExpression):
    def __init__(
        self,
        expr: Token | Any,
        lower: Token | Any = None,
        upper: Token | Any = None,
        variable: Token | Any = None,
    ):
        """An integral expression, such as `\\int_{a}^{b} f(x) dx`."""
        super().__init__(
            "int", expr, lower, upper, Macro(",") & Macro("mathrm", "d") & variable
        )


class Limit(LimitsExpression):
    def __init__(
        self, expr: Token | Any, variable: Token | Any = None, limit: Token | Any = None
    ):
        """A limit expression, such as `\\lim_{x \\to a} f(x)`."""
        lower_expr = None
        if variable is not None and limit is not None:
            lower_expr = Tends(variable, limit)
        elif variable is not None:
            lower_expr = as_token(variable)
        elif limit is not None:
            lower_expr = as_token(limit)
        super().__init__("lim", expr, lower=lower_expr)


class Summation(LimitsExpression):
    def __init__(
        self,
        expr: Token | Any,
        lower: Token | Any = None,
        variable: Token | Any = None,
        upper: Token | Any = None,
    ):
        """A summation expression, such as `\\sum_{i = 0}^{n} a_i`."""
        if lower is None and variable is None:
            lower_expr = None
        elif lower is None:
            lower_expr = as_token(variable)
        elif variable is None:
            lower_expr = as_token(lower)
        else:
            lower_expr = as_token(variable) == as_token(lower)
        super().__init__("sum", expr, lower=lower_expr, upper=upper)


class Derivative(Token):
    def __init__(
        self,
        numerator_expr: Token | Any,
        denominator_expr: Token | Any,
        order: int | Token | Any = 1,
        as_operator: bool = False,
    ):
        r"""A derivative expression, such as `\frac{\mathrm{d}^2 y}{\mathrm{d} x^2}`."""
        self.numerator_expr = as_token(numerator_expr)
        self.denominator_expr = as_token(denominator_expr)
        self.order = as_token(order) if order != 1 else None
        self.as_operator = as_operator
        self.derivative_operator = Macro("mathrm", "d")

    def __str__(self) -> str:
        if self.order is None:
            if self.as_operator:
                return str(
                    (self.derivative_operator)
                    / (self.derivative_operator & self.denominator_expr)
                    & self.numerator_expr
                )
            return str(
                (self.derivative_operator & self.numerator_expr)
                / (self.derivative_operator & self.denominator_expr)
            )
        if self.as_operator:
            return str(
                (self.derivative_operator**self.order)
                / (self.derivative_operator & (self.denominator_expr**self.order))
                & self.numerator_expr
            )
        return str(
            (self.derivative_operator**self.order & self.numerator_expr)
            / (self.derivative_operator & self.denominator_expr**self.order)
        )


class PartialDerivative(Derivative):
    def __init__(
        self,
        numerator_expr: Token | Any,
        *denominator_expr: Token | Any,
        order: int | Token | Any = 1,
        as_operator: bool = False,
    ):
        r"""A partial derivative expression, such as `\frac{\partial^2 y}{\partial x^2}`."""
        super().__init__(numerator_expr, denominator_expr, order, as_operator)
        self.denominator_expr = (as_token(expr) for expr in denominator_expr)
        self.denominator_expr_orders = dict()
        for expr in denominator_expr:
            if expr in self.denominator_expr_orders:
                self.denominator_expr_orders[expr] += 1
            else:
                self.denominator_expr_orders[expr] = 1
        total_order = sum(self.denominator_expr_orders.values())
        if isinstance(order, int):
            if order > total_order:
                diff = order - total_order
                self.denominator_expr_orders[denominator_expr[-1]] += diff
                total_order = order
            elif order < total_order and order != 1:
                raise ValueError(
                    f"Order of partial derivative ({order}) is less than the number of denominator expressions ({total_order})"
                )
        self.order = as_token(total_order) if total_order != 1 else None
        self.derivative_operator = Macro("partial")

    def __str__(self) -> str:
        if self.as_operator:
            if self.order is None:
                numerator = self.derivative_operator
            else:
                numerator = self.derivative_operator**self.order
            post = self.numerator_expr
        else:
            if self.order is None:
                numerator = self.derivative_operator & self.numerator_expr
            else:
                numerator = self.derivative_operator**self.order & self.numerator_expr
            post = Literal("")
        denominator = []
        for expr, order in self.denominator_expr_orders.items():
            if order == 1:
                denominator.append(self.derivative_operator & expr)
            else:
                denominator.append(self.derivative_operator & expr**order)

        return str(numerator / Collection(*denominator) & post)


__all__ = [
    "Tends",
    "LimitsExpression",
    "Integral",
    "Limit",
    "Summation",
    "Derivative",
    "PartialDerivative",
]

