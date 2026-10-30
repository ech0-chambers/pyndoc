"""Core AST grammar, base tokens, operators, and coercion registry."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any, Callable, Set
import pint
from .config import ACTIVE_CONFIG


_TOKEN_CONVERTERS: List[Tuple[type | Tuple[type, ...], Callable[[Any], "Token"]]] = []
_UNIT_PARSER: Optional[Callable[[Any], pint.Unit]] = None


def register_token_converter(
    types: type | Tuple[type, ...], converter: Callable[[Any], "Token"]
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

    def __add__(self, other: "Token") -> "Addition":
        return Addition(self, other)

    def __radd__(self, other: "Token") -> "Addition":
        return Addition(other, self)

    def __sub__(self, other: "Token") -> "Subtraction":
        return Subtraction(self, other)

    def __rsub__(self, other: "Token") -> "Subtraction":
        return Subtraction(other, self)

    def __mul__(self, other: "Token") -> "Multiplication":
        return Multiplication(self, other)

    def __rmul__(self, other: "Token") -> "Multiplication":
        return Multiplication(other, self)

    def __matmul__(self, other: "Token") -> "Times":
        return Times(self, other)

    def __rmatmul__(self, other: "Token") -> "Times":
        return Times(other, self)

    def __div__(self, other: "Token") -> "Division":
        return Division(self, other)

    def __rdiv__(self, other: "Token") -> "Division":
        return Division(other, self)

    def __truediv__(self, other: "Token") -> "Division":
        return Division(self, other)

    def __rtruediv__(self, other: "Token") -> "Division":
        return Division(other, self)

    def __pow__(self, other: "Token") -> "Power":
        return Power(self, other)

    def __rpow__(self, other: "Token") -> "Power":
        return Power(other, self)

    def __getitem__(self, other: "Token") -> "Index":
        return Index(self, other)

    def __and__(self, other: "Token") -> "Concatenation":
        return Concatenation(self, other)

    def __rand__(self, other: "Token") -> "Concatenation":
        return Concatenation(other, self)

    def __neg__(self) -> "Negation":
        return Negation(self)

    def __pos__(self) -> "Positive":
        return Positive(self)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: Any) -> "Equality":
        return Equality(self, other)

    def __lt__(self, other: Any) -> "LessThan":
        return LessThan(self, other)

    def __gt__(self, other: Any) -> "GreaterThan":
        return GreaterThan(self, other)

    def __le__(self, other: Any) -> "LessThanOrEqual":
        return LessThanOrEqual(self, other)

    def __ge__(self, other: Any) -> "GreaterThanOrEqual":
        return GreaterThanOrEqual(self, other)

    def __ne__(self, other: Any) -> "NotEqual":
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


class CallableToken(Token, ABC):
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
        arg: str | Token | Dict[str, Any],
        is_optional: bool = False,
        in_expl3: bool = False,
    ):
        """An argument to a macro or environment.

        Parameters
        ----------
        arg : str | Token | Dict[str, Any]
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
                arg = {
                    key.replace(" ", "~"): value.replace(" ", "~")
                    for key, value in self.arg.items()
                }
            else:
                arg = self.arg
            return f"{open_delim}{', '.join([f'{key}={value}' for key, value in arg.items()])}{close_delim}"

        arg = str(self.arg)
        if self.in_expl3:
            arg = arg.replace(" ", "~")
        return f"{open_delim}{arg}{close_delim}"


class Macro(Token):
    def __init__(
        self,
        name: str,
        *arguments: str | Tuple[str, bool] | Argument,
        in_expl3: bool = False,
    ):
        r"""A LaTeX macro, optionally with arguments.

        Parameters
        ----------
        name : str
            The name of the macro. For example, `Macro("LaTeX")` renders as `\LaTeX`.
        arguments : Tuple[Argument]
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
        *arguments: str | Tuple[str, bool] | Argument,
        content: str | Token | List[Token] = None,
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

    def __init__(self, value: CallableToken | str | float) -> None:
        self.right = as_token(value)
        self.symbol = ""
        self._unit: Optional[pint.Unit] = None

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
        return as_token(value)(*args, **kwargs)

    @abstractmethod
    def _operation(self, value: CallableToken) -> Any:
        pass

    @property
    def value(self) -> Any:
        val = self._operation(self.right)
        if self._unit is not None and isinstance(val, pint.Quantity):
            val = val.to(self._unit)
        return val

    @property
    def unit(self) -> Optional[pint.Unit]:
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

    def __init__(self, value: CallableToken | str | float) -> None:
        """Negates a value, such as `-a`."""
        super().__init__(value)
        self.symbol = "-"

    def _operation(self, value: CallableToken) -> Any:
        return -value.value


class Positive(_UnaryOperator):
    precedence = 30

    def __init__(self, value: CallableToken | str | float) -> None:
        """Returns the positive value of a quantity, such as `+a`."""
        super().__init__(value)
        self.symbol = "+"

    def _operation(self, value: CallableToken) -> Any:
        return value.value


class _BinaryOperator(CallableToken, ABC):
    precedence: int = 0
    is_associative: bool = True
    bracket_left: bool = True
    bracket_right: bool = True

    def __init__(
        self,
        left: CallableToken | str | float,
        right: CallableToken | str | float,
    ) -> None:
        self.left = as_token(left)
        self.right = as_token(right)
        self.symbol = ""
        self._unit: Optional[pint.Unit] = None

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
        return as_token(value)(*args, **kwargs)

    @abstractmethod
    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        pass

    @property
    def value(self) -> Any:
        val = self._operation(self.left, self.right)
        if self._unit is not None and isinstance(val, pint.Quantity):
            val = val.to(self._unit)
        return val

    @property
    def unit(self) -> Optional[pint.Unit]:
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
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        """Adds two values together, such as `a + b`."""
        super().__init__(left, right)
        self.symbol = "+"

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value + right.value


class Subtraction(_BinaryOperator):
    precedence = 10
    is_associative = False
    bracket_left = True
    bracket_right = True

    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        """Subtracts one value from another, such as `a - b`."""
        super().__init__(left, right)
        self.symbol = "-"

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value - right.value


class Multiplication(_BinaryOperator):
    precedence = 20
    is_associative = True
    bracket_left = True
    bracket_right = True

    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        """Multiplies two values together, such as `a * b`. This is rendered as `ab`."""
        super().__init__(left, right)
        self.symbol = ""

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value * right.value


class Times(_BinaryOperator):
    precedence = 20
    is_associative = True
    bracket_left = True
    bracket_right = True

    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        r"""Multiplies two values together, such as `a * b`.
        Rendered as `a \times b` (or configured multiplication_operator).
        """
        super().__init__(left, right)
        self._custom_symbol: Optional[str] = None

    @property
    def symbol(self) -> str:
        if self._custom_symbol is not None:
            return self._custom_symbol
        return ACTIVE_CONFIG.multiplication_operator

    @symbol.setter
    def symbol(self, value: Optional[str]) -> None:
        self._custom_symbol = value

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value * right.value


class Division(_BinaryOperator):
    precedence = 20
    bracket_left = False
    bracket_right = False

    def __init__(
        self,
        left: CallableToken | str | float,
        right: CallableToken | str | float,
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

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value / right.value

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
        left: CallableToken | str | float,
        right: CallableToken | str | float,
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

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value**right.value

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
        left: CallableToken | str | float,
        right: CallableToken | str | float,
    ) -> None:
        """Indexes one value with another, such as `a_i`."""
        super().__init__(left, right)
        self.symbol = "_"

    def _should_group_operand(self, operand: Token, is_right: bool = False) -> bool:
        if is_right:
            return True
        return super()._should_group_operand(operand, is_right=False)

    def _operation(self, left: CallableToken, right: CallableToken) -> None:
        pass

    def __str__(self) -> str:
        left = self.format_operand(self.left, is_right=False)
        right = self.format_operand(self.right, is_right=True)
        return f"{left}{self.symbol}{right}"


class Concatenation(Token):
    def __init__(self, *args: CallableToken) -> None:
        """Concatenates a number of values together, such as `Concatenation(a, b, c)` --> `abc`."""
        self.args = args

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

    @abstractmethod
    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        pass


class Equality(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        """Equality between two expressions, such as `a = b`."""
        super().__init__(left, right)
        self.symbol = "="

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value == right.value


class LessThan(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        """Inequality between two expressions, such as `a < b`."""
        super().__init__(left, right)
        self.symbol = "<"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value < right.value


class GreaterThan(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        """Inequality between two expressions, such as `a > b`."""
        super().__init__(left, right)
        self.symbol = ">"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value > right.value


class LessThanOrEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        r"""Inequality between two expressions, such as `a <= b` (\leq)."""
        super().__init__(left, right)
        self.symbol = "\\leq"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value <= right.value


class GreaterThanOrEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        r"""Inequality between two expressions, such as `a >= b` (\geq)."""
        super().__init__(left, right)
        self.symbol = "\\geq"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value >= right.value


class NotEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        r"""Inequality between two expressions, such as `a != b` (\neq)."""
        super().__init__(left, right)
        self.symbol = "\\neq"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value != right.value


class Approximation(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        r"""Approximate equality between two expressions, such as `a \approx b`."""
        super().__init__(left, right)
        self.symbol = "\\approx"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value == right.value


class Equivalence(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> None:
        r"""Logical equivalence between two expressions, such as `a \equiv b`."""
        super().__init__(left, right)
        self.symbol = "\\equiv"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value == right.value


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


