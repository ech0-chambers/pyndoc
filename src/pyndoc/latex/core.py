"""Core AST grammar, base tokens, operators, and coercion registry."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeAlias, Union

import pint

from .config import ACTIVE_CONFIG

_TOKEN_CONVERTERS: list[tuple[type | tuple[type, ...], Callable[[Any], "Token"]]] = []
_UNIT_PARSER: Callable[[Any], pint.Unit] | None = None


def register_token_converter(
    types: type | tuple[type, ...], converter: Callable[[Any], "Token"]
) -> None:
    """Register a converter function to coerce external types into Token instances.

    Parameters
    ----------
    types : type | Tuple[type, ...]
        Python type or tuple of types to match.
    converter : Callable[[Any], Token]
        Callable taking the value and returning a Token subclass instance.
    """
    _TOKEN_CONVERTERS.append((types, converter))


def set_unit_parser(parser: Callable[[Any], pint.Unit]) -> None:
    """Set the unit parser function to decouple unit parsing from core AST nodes."""
    global _UNIT_PARSER
    _UNIT_PARSER = parser


TokenLike: TypeAlias = Union["Token", str, float, int]


def _get_evaluable_operand_value(operand: Any) -> Any:
    """Extract a numeric or Quantity value from an operand if evaluable, else return None."""
    val = getattr(operand, "value", operand)
    if val is None or isinstance(val, Token):
        return None
    if isinstance(val, (int, float, complex, pint.Quantity)):
        return val
    if isinstance(val, str):
        try:
            f = float(val)
            return int(f) if f.is_integer() else f
        except ValueError:
            return None
    return None


def _parse_unit(unit: Any) -> pint.Unit:
    """Parse a unit using the registered unit parser if available."""
    if isinstance(unit, pint.Unit):
        return unit
    if _UNIT_PARSER is not None:
        return _UNIT_PARSER(unit)
    return pint.Unit(unit)


class Token(ABC):
    precedence: int = 100

    @abstractmethod
    def __str__(self) -> str:
        pass

    def __add__(self, other: Any) -> "Addition":
        return Addition(self, other)

    def __radd__(self, other: Any) -> "Addition":
        return Addition(other, self)

    def __sub__(self, other: Any) -> "Subtraction":
        return Subtraction(self, other)

    def __rsub__(self, other: Any) -> "Subtraction":
        return Subtraction(other, self)

    def __mul__(self, other: Any) -> "Multiplication":
        return Multiplication(self, other)

    def __rmul__(self, other: Any) -> "Multiplication":
        return Multiplication(other, self)

    def __matmul__(self, other: Any) -> "Times":
        return Times(self, other)

    def __rmatmul__(self, other: Any) -> "Times":
        return Times(other, self)

    def __div__(self, other: Any) -> "Division":
        return Division(self, other)

    def __rdiv__(self, other: Any) -> "Division":
        return Division(other, self)

    def __truediv__(self, other: Any) -> "Division":
        return Division(self, other)

    def __rtruediv__(self, other: Any) -> "Division":
        return Division(other, self)

    def __pow__(self, other: Any) -> "Power":
        return Power(self, other)

    def __rpow__(self, other: Any) -> "Power":
        return Power(other, self)

    def __getitem__(self, other: Any) -> Any:
        return Index(self, other)

    def __and__(self, other: Any) -> "Concatenation":
        return Concatenation(self, other)

    def __rand__(self, other: Any) -> "Concatenation":
        return Concatenation(other, self)

    def __neg__(self) -> "Negation":
        return Negation(self)

    def __pos__(self) -> "Positive":
        return Positive(self)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: Any) -> Any:
        if other is None:
            return False
        return Equality(self, other)

    def __lt__(self, other: Any) -> "LessThan":
        return LessThan(self, other)

    def __gt__(self, other: Any) -> "GreaterThan":
        return GreaterThan(self, other)

    def __le__(self, other: Any) -> "LessThanOrEqual":
        return LessThanOrEqual(self, other)

    def __ge__(self, other: Any) -> "GreaterThanOrEqual":
        return GreaterThanOrEqual(self, other)

    def __ne__(self, other: Any) -> Any:
        if other is None:
            return True
        return NotEqual(self, other)

    def __abs__(self) -> "Token":
        raise TypeError(
            f"Direct Python abs() is not supported on {type(self).__name__}. "
            "Use tex.abs() or tex.absolute() instead."
        )

    def approx(self, other: Any) -> "Approximation":
        return Approximation(self, other)

    def equiv(self, other: Any) -> "Equivalence":
        return Equivalence(self, other)


class Literal(Token):
    def __init__(self, value: str | float) -> None:
        """Contains a string or float to handle its behaviour for typesetting.

        Parameters
        ----------
        value : str | float
            The value of the literal
        """
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


class DimensionedLiteral(Literal):
    # differentiates from a regular Literal so that operators like Power can bracket appropriately.
    def __init__(self, value: str | float) -> None:
        """Contains a string or float to handle its behaviour for typesetting.
        This differs from a Literal in that it is assumed to also contain units,
        and so some operators may treat it differently for bracketing purposes.

        Parameters
        ----------
        value : str | float
            The value of the literal
        """
        super().__init__(value)


class BooleanLiteral(Literal):
    """Boolean literal representation, rendering as `\\mathrm{True}` or `\\mathrm{False}`."""

    def __init__(self, value: bool) -> None:
        super().__init__(str(value))
        self.value: bool = bool(value)

    def __str__(self) -> str:
        return f"\\mathrm{{{self.value}}}"

    def __bool__(self) -> bool:
        return self.value


class CallableToken(Token, ABC):
    value: Any

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        pass

    def as_quantity(self) -> Any:
        """Convert the callable token to a Quantity with its current evaluated value."""
        return as_token(self.value)

    def __float__(self) -> float:
        val = self.value
        if isinstance(val, pint.Quantity):
            return float(val.magnitude)
        return float(val)

    def __int__(self) -> int:
        val = self.value
        if isinstance(val, pint.Quantity):
            return int(val.magnitude)
        return int(val)


class Argument:
    def __init__(
        self,
        arg: TokenLike | dict[str, Any],
        is_optional: bool = False,
        in_expl3: bool = False,
    ):
        """An argument to a macro or environment.

        Parameters
        ----------
        arg : TokenLike | Dict[str, Any]
            The argument to the macro or environment. This can be a dictionary of key-value pairs,
            in which case they will be formatted as key=value.
        is_optional : bool, optional
            If True, the argument will be rendered as optional, using square brackets instead of braces.
        in_expl3 : bool, optional
            If True, spaces in the argument are replaced with `~`.
        """
        self.arg = arg
        self.optional = is_optional
        self.in_expl3 = in_expl3

    def __str__(self) -> str:
        open_delim = "[" if self.optional else "{"
        close_delim = "]" if self.optional else "}"

        if isinstance(self.arg, dict):
            if self.in_expl3:
                dict_arg = {
                    key.replace(" ", "~"): value.replace(" ", "~")
                    for key, value in self.arg.items()
                }
            else:
                dict_arg = self.arg
            return f"{open_delim}{', '.join([f'{key}={value}' for key, value in dict_arg.items()])}{close_delim}"

        str_arg = str(self.arg)
        if self.in_expl3:
            str_arg = str_arg.replace(" ", "~")
        return f"{open_delim}{str_arg}{close_delim}"


class Macro(Token):
    def __init__(
        self,
        name: str,
        *arguments: TokenLike | tuple[TokenLike, bool] | dict[str, Any] | Argument,
        in_expl3: bool = False,
    ):
        r"""A LaTeX macro, optionally with arguments.

        Parameters
        ----------
        name : str
            The name of the macro. For example, `Macro("LaTeX")` renders as `\LaTeX`.
        arguments : TokenLike | Tuple[TokenLike, bool] | Dict[str, Any] | Argument
            Arguments for the macro.
        in_expl3 : bool, optional
            If True, spaces in arguments will be replaced with `~`.
        """
        self.name = name
        self.arguments = arguments
        self.in_expl3 = in_expl3

    def __str__(self) -> str:
        out = "\\" + self.name

        for arg in self.arguments:
            if isinstance(arg, Argument):
                out += str(arg)
            elif isinstance(arg, tuple):
                out += str(
                    Argument(arg[0], is_optional=arg[1], in_expl3=self.in_expl3)
                )
            else:
                out += str(Argument(arg, in_expl3=self.in_expl3))

        return out


class Environment(Token):
    def __init__(
        self,
        name: str,
        *arguments: TokenLike | tuple[TokenLike, bool] | dict[str, Any] | Argument,
        content: str | Token | list[Token] | None = None,
        in_expl3: bool = False,
    ):
        r"""A LaTeX environment, optionally with arguments.

        Parameters
        ----------
        name : str
            The name of the environment.
        arguments : str | Tuple[str, bool] | Argument, optional
            Arguments for the environment.
        content : str | Token | List[Token], optional
            The content of the environment.
        in_expl3 : bool, optional
            If True, spaces in arguments will be replaced with `~`.
        """
        self.name = name
        self.arguments = arguments
        self.content = content
        self.in_expl3 = in_expl3

    def __str__(self) -> str:
        out = str(Macro("begin", self.name, *self.arguments, in_expl3=self.in_expl3))
        if self.content is not None:
            if isinstance(self.content, (list, tuple)):
                out += "".join([str(expr) for expr in self.content])
            else:
                out += str(self.content)
        out += str(Macro("end", self.name))
        return out


def as_token(value: Any) -> Token:
    """Coerce any value into a Token AST node.

    Parameters
    ----------
    value : Any
        The value to be converted.

    Returns
    -------
    Token
        The converted Token AST node.
    """
    if isinstance(value, Token):
        return value
    if isinstance(value, bool):
        return BooleanLiteral(value)
    if isinstance(value, str):
        if value.isnumeric():
            val = float(value)
            if val.is_integer():
                val = int(val)
            for types, converter in _TOKEN_CONVERTERS:
                if isinstance(val, types):
                    return converter(val)
            return Literal(value)
        return Literal(value)
    for types, converter in _TOKEN_CONVERTERS:
        if isinstance(value, types):
            return converter(value)
    raise TypeError(f"Cannot coerce {type(value).__name__} to a Token")


sym = as_token
symbol = as_token


class _UnaryOperator(CallableToken, ABC):
    precedence: int = 30
    bracket_right: bool = True

    def __init__(self, value: TokenLike) -> None:
        self.right = as_token(value)
        self.symbol = ""
        self._unit: pint.Unit | None = None

    def _should_group_operand(self, operand: Token) -> bool:
        operand_precedence = getattr(operand, "precedence", 100)
        return operand_precedence < self.precedence

    def format_operand(self, operand: Token) -> str:
        if self._should_group_operand(operand):
            if self.bracket_right:
                return f"\\left({operand}\\right)"
            return f"{{{operand}}}"
        return str(operand)

    def __str__(self) -> str:
        return f"{self.symbol}{self.format_operand(self.right)}"

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        value = self.value
        if value is None:
            raise ValueError(
                f"Cannot numerically evaluate expression '{self}' because operand does not have a numeric value."
            )
        tok = as_token(value)
        if isinstance(tok, CallableToken):
            return tok(*args, **kwargs)
        return Literal(str(value))

    @abstractmethod
    def _operation(self, value: Any) -> Any:
        pass

    @property
    def value(self) -> Any:
        rv = _get_evaluable_operand_value(self.right)
        if rv is None:
            return None
        try:
            val = self._operation(rv)
            if self._unit is not None and isinstance(val, pint.Quantity):
                val = val.to(self._unit)
            return val
        except (TypeError, ValueError):
            return None

    @property
    def unit(self) -> pint.Unit | None:
        if self._unit is not None:
            return self._unit
        val = self.value
        if isinstance(val, pint.Quantity):
            return val.units
        return None

    @unit.setter
    def unit(self, unit: pint.Unit | str) -> None:
        val = self.value
        if isinstance(val, pint.Quantity):
            self._unit = _parse_unit(unit)
        else:
            raise ValueError(
                f"Cannot set unit of non-Quantity of type {str(type(val)).replace('<', '').replace('>', '')}"
            )


class Negation(_UnaryOperator):
    precedence = 30

    def __init__(self, value: TokenLike) -> None:
        """Negates a value, such as `-a`."""
        super().__init__(value)
        self.symbol = "-"

    def _operation(self, value: Any) -> Any:
        return -value


class Positive(_UnaryOperator):
    precedence = 30

    def __init__(self, value: TokenLike) -> None:
        """Returns the positive value of a quantity, such as `+a`."""
        super().__init__(value)
        self.symbol = "+"

    def _operation(self, value: Any) -> Any:
        return value


class _BinaryOperator(CallableToken, ABC):
    precedence: int = 0
    is_associative: bool = True
    bracket_left: bool = True
    bracket_right: bool = True

    def __init__(
        self,
        left: TokenLike,
        right: TokenLike,
    ) -> None:
        self.left = as_token(left)
        self.right = as_token(right)
        self.symbol = ""
        self._unit: pint.Unit | None = None

    def _should_group_operand(self, operand: Token, is_right: bool = False) -> bool:
        operand_precedence = getattr(operand, "precedence", 100)
        if operand_precedence < self.precedence:
            return True
        if is_right and operand_precedence == self.precedence and not getattr(self, "is_associative", True):
            return True
        return False

    def format_operand(self, operand: Token, is_right: bool = False) -> str:
        if self._should_group_operand(operand, is_right=is_right):
            use_brackets = self.bracket_right if is_right else self.bracket_left
            if use_brackets:
                return f"\\left({operand}\\right)"
            return f"{{{operand}}}"
        return str(operand)

    def __str__(self) -> str:
        left = self.format_operand(self.left, is_right=False)
        right = self.format_operand(self.right, is_right=True)
        if not self.symbol:
            return f"{left} {right}"
        return f"{left} {self.symbol} {right}"

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        value = self.value
        if value is None:
            raise ValueError(
                f"Cannot numerically evaluate expression '{self}' because one or more operands do not have a numeric value."
            )
        tok = as_token(value)
        if isinstance(tok, CallableToken):
            return tok(*args, **kwargs)
        return Literal(str(value))

    @abstractmethod
    def _operation(self, left: Any, right: Any) -> Any:
        pass

    @property
    def value(self) -> Any:
        lv = _get_evaluable_operand_value(self.left)
        rv = _get_evaluable_operand_value(self.right)
        if lv is None or rv is None:
            return None
        try:
            val = self._operation(lv, rv)
            if self._unit is not None and isinstance(val, pint.Quantity):
                val = val.to(self._unit)
            return val
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    @property
    def unit(self) -> pint.Unit | None:
        if self._unit is not None:
            return self._unit
        val = self.value
        if isinstance(val, pint.Quantity):
            return val.units
        return None

    @unit.setter
    def unit(self, unit: pint.Unit | str) -> None:
        val = self.value
        if isinstance(val, pint.Quantity):
            self._unit = _parse_unit(unit)
        else:
            raise ValueError(
                f"Cannot set unit of non-Quantity of type {str(type(val)).replace('<', '').replace('>', '')}"
            )


class Addition(_BinaryOperator):
    precedence = 10
    is_associative = True
    bracket_left = True
    bracket_right = True

    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        """Adds two values together, such as `a + b`."""
        super().__init__(left, right)
        self.symbol = "+"

    def _operation(self, left: Any, right: Any) -> Any:
        return left + right


class Subtraction(_BinaryOperator):
    precedence = 10
    is_associative = False
    bracket_left = True
    bracket_right = True

    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        """Subtracts one value from another, such as `a - b`."""
        super().__init__(left, right)
        self.symbol = "-"

    def _operation(self, left: Any, right: Any) -> Any:
        return left - right


class Multiplication(_BinaryOperator):
    precedence = 20
    is_associative = True
    bracket_left = True
    bracket_right = True

    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        """Multiplies two values together, such as `a * b`. This is rendered as `ab`."""
        super().__init__(left, right)
        self.symbol = ""

    def _operation(self, left: Any, right: Any) -> Any:
        return left * right


class Times(_BinaryOperator):
    precedence = 20
    is_associative = True
    bracket_left = True
    bracket_right = True

    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        r"""Multiplies two values together, such as `a * b`.
        Rendered as `a \times b` (or configured multiplication_operator).
        """
        super().__init__(left, right)
        self._custom_symbol: str | None = None

    @property
    def symbol(self) -> str:
        if self._custom_symbol is not None:
            return self._custom_symbol
        return ACTIVE_CONFIG.multiplication_operator

    @symbol.setter
    def symbol(self, value: str | None) -> None:
        self._custom_symbol = value

    def _operation(self, left: Any, right: Any) -> Any:
        return left * right


class Division(_BinaryOperator):
    precedence = 20
    bracket_left = False
    bracket_right = False

    def __init__(
        self,
        left: TokenLike,
        right: TokenLike,
        display_mode: bool = False,
    ) -> None:
        r"""Divides one value by another, rendered as `\frac{a}{b}` or `\dfrac{a}{b}`."""
        super().__init__(left, right)
        if display_mode:
            self.symbol = "\\dfrac"
        else:
            self.symbol = "\\frac"

    def _should_group_operand(self, operand: Token, is_right: bool = False) -> bool:
        return True

    def _operation(self, left: Any, right: Any) -> Any:
        return left / right

    def __str__(self) -> str:
        left = self.format_operand(self.left, is_right=False)
        right = self.format_operand(self.right, is_right=True)
        return f"{self.symbol}{left}{right}"


class Power(_BinaryOperator):
    precedence = 40
    is_associative = False
    bracket_left = True
    bracket_right = False

    def __init__(
        self,
        left: TokenLike,
        right: TokenLike,
    ) -> None:
        """Raises one value to the power of another, such as `a ** b`."""
        super().__init__(left, right)
        self.symbol = "^"

    def _should_group_operand(self, operand: Token, is_right: bool = False) -> bool:
        if is_right:
            return True
        if isinstance(operand, DimensionedLiteral):
            return True
        return super()._should_group_operand(operand, is_right=False)

    def _operation(self, left: Any, right: Any) -> Any:
        return left**right

    def __str__(self) -> str:
        left = self.format_operand(self.left, is_right=False)
        right = self.format_operand(self.right, is_right=True)
        return f"{left}{self.symbol}{right}"


class Index(_BinaryOperator):
    precedence = 40
    bracket_left = True
    bracket_right = False

    def __init__(
        self,
        left: TokenLike,
        right: TokenLike,
    ) -> None:
        """Indexes one value with another, such as `a_i`."""
        super().__init__(left, right)
        self.symbol = "_"

    def _should_group_operand(self, operand: Token, is_right: bool = False) -> bool:
        if is_right:
            return True
        return super()._should_group_operand(operand, is_right=False)

    def _operation(self, left: Any, right: Any) -> None:
        pass

    def __str__(self) -> str:
        left = self.format_operand(self.left, is_right=False)
        right = self.format_operand(self.right, is_right=True)
        return f"{left}{self.symbol}{right}"


class Concatenation(Token):
    def __init__(self, *args: TokenLike) -> None:
        """Concatenates a number of values together, such as `Concatenation(a, b, c)` --> `abc`."""
        self.args = tuple(as_token(arg) for arg in args)

    def __str__(self) -> str:
        return " ".join(str(arg) for arg in self.args)


class _BooleanBinaryOperator(_BinaryOperator):
    precedence = 0
    is_associative = True
    bracket_left = True
    bracket_right = True

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        value = self._operation(self.left, self.right)
        return Literal(str(value))

    def __bool__(self) -> bool:
        # 1. If comparing against None, Equality is False and NotEqual is True
        if self.left is None or self.right is None:
            if isinstance(self, Equality):
                return False
            if isinstance(self, NotEqual):
                return True

        # 2. If both operands have evaluable values, evaluate via _operation
        try:
            left_val = getattr(self.left, "value", None)
            right_val = getattr(self.right, "value", None)
            if left_val is not None and right_val is not None:
                return bool(self._operation(self.left, self.right))
        except Exception:
            pass

        # 3. Structural identity shortcuts for Equality and NotEqual
        if isinstance(self, Equality):
            if str(self.left) == str(self.right):
                return True
            if isinstance(self.left, Literal) and isinstance(self.right, Literal):
                return False
        elif isinstance(self, NotEqual):
            if str(self.left) == str(self.right):
                return False
            if isinstance(self.left, Literal) and isinstance(self.right, Literal):
                return True

        # 4. Otherwise, cannot determine boolean truth value of symbolic relation
        raise TypeError(
            f"Cannot determine truth value of symbolic LaTeX relation '{self}'. "
            "Use expr.value to compare evaluated values, or str(expr) to compare representations."
        )

    @staticmethod
    def _coerce_operands_for_comparison(left_val: Any, right_val: Any) -> tuple[Any, Any]:
        if isinstance(left_val, (int, float)) and isinstance(right_val, str):
            try:
                converted = float(right_val)
                if isinstance(left_val, int) and converted.is_integer():
                    return left_val, int(converted)
                return left_val, converted
            except (ValueError, TypeError):
                pass
        elif isinstance(right_val, (int, float)) and isinstance(left_val, str):
            try:
                converted = float(left_val)
                if isinstance(right_val, int) and converted.is_integer():
                    return int(converted), right_val
                return converted, right_val
            except (ValueError, TypeError):
                pass
        return left_val, right_val

    @abstractmethod
    def _operation(self, left: Any, right: Any) -> bool:
        pass


class Equality(_BooleanBinaryOperator):
    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        """Equality between two expressions, such as `a = b`."""
        super().__init__(left, right)
        self.symbol = "="

    def _operation(self, left: Any, right: Any) -> bool:
        lv = getattr(left, "value", left)
        rv = getattr(right, "value", right)
        lv_coerced, rv_coerced = self._coerce_operands_for_comparison(lv, rv)
        return lv_coerced == rv_coerced


class LessThan(_BooleanBinaryOperator):
    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        """Inequality between two expressions, such as `a < b`."""
        super().__init__(left, right)
        self.symbol = "<"

    def _operation(self, left: Any, right: Any) -> bool:
        lv = getattr(left, "value", left)
        rv = getattr(right, "value", right)
        lv_coerced, rv_coerced = self._coerce_operands_for_comparison(lv, rv)
        return lv_coerced < rv_coerced


class GreaterThan(_BooleanBinaryOperator):
    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        """Inequality between two expressions, such as `a > b`."""
        super().__init__(left, right)
        self.symbol = ">"

    def _operation(self, left: Any, right: Any) -> bool:
        lv = getattr(left, "value", left)
        rv = getattr(right, "value", right)
        lv_coerced, rv_coerced = self._coerce_operands_for_comparison(lv, rv)
        return lv_coerced > rv_coerced


class LessThanOrEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        r"""Inequality between two expressions, such as `a <= b` (\leq)."""
        super().__init__(left, right)
        self.symbol = "\\leq"

    def _operation(self, left: Any, right: Any) -> bool:
        lv = getattr(left, "value", left)
        rv = getattr(right, "value", right)
        lv_coerced, rv_coerced = self._coerce_operands_for_comparison(lv, rv)
        return lv_coerced <= rv_coerced


class GreaterThanOrEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        r"""Inequality between two expressions, such as `a >= b` (\geq)."""
        super().__init__(left, right)
        self.symbol = "\\geq"

    def _operation(self, left: Any, right: Any) -> bool:
        lv = getattr(left, "value", left)
        rv = getattr(right, "value", right)
        lv_coerced, rv_coerced = self._coerce_operands_for_comparison(lv, rv)
        return lv_coerced >= rv_coerced


class NotEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        r"""Inequality between two expressions, such as `a != b` (\neq)."""
        super().__init__(left, right)
        self.symbol = "\\neq"

    def _operation(self, left: Any, right: Any) -> bool:
        lv = getattr(left, "value", left)
        rv = getattr(right, "value", right)
        lv_coerced, rv_coerced = self._coerce_operands_for_comparison(lv, rv)
        return lv_coerced != rv_coerced


class Approximation(_BooleanBinaryOperator):
    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        r"""Approximate equality between two expressions, such as `a \approx b`."""
        super().__init__(left, right)
        self.symbol = "\\approx"

    def _operation(self, left: Any, right: Any) -> bool:
        lv = getattr(left, "value", left)
        rv = getattr(right, "value", right)
        return lv == rv


class Equivalence(_BooleanBinaryOperator):
    def __init__(
        self, left: TokenLike, right: TokenLike
    ) -> None:
        r"""Logical equivalence between two expressions, such as `a \equiv b`."""
        super().__init__(left, right)
        self.symbol = "\\equiv"

    def _operation(self, left: Any, right: Any) -> bool:
        lv = getattr(left, "value", left)
        rv = getattr(right, "value", right)
        return lv == rv


def approx(left: Any, right: Any) -> Approximation:
    r"""Create an approximate equality expression: `a \approx b`."""
    return Approximation(left, right)


def equiv(left: Any, right: Any) -> Equivalence:
    r"""Create a logical equivalence expression: `a \equiv b`."""
    return Equivalence(left, right)


__all__ = [
    "Token",
    "CallableToken",
    "Literal",
    "DimensionedLiteral",
    "BooleanLiteral",
    "Argument",
    "Macro",
    "Environment",
    "_UnaryOperator",
    "Negation",
    "Positive",
    "_BinaryOperator",
    "Addition",
    "Subtraction",
    "Multiplication",
    "Times",
    "Division",
    "Power",
    "Index",
    "Concatenation",
    "_BooleanBinaryOperator",
    "Equality",
    "LessThan",
    "GreaterThan",
    "LessThanOrEqual",
    "GreaterThanOrEqual",
    "NotEqual",
    "Approximation",
    "Equivalence",
    "approx",
    "equiv",
    "as_token",
    "sym",
    "symbol",
    "register_token_converter",
    "set_unit_parser",
]


