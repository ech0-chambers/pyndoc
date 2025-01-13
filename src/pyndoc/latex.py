from abc import ABC, abstractmethod
from typing import List, Optional, Set, Tuple, Dict, Any
import pint
import numpy as np
import re

ureg = pint.UnitRegistry()
ureg.define("electronvolt = 1.602176634e-19 * joules = eV")
ureg.define("clight = 299792458 * m/s = c")
ureg.define("year = 365.25 * day = yr")
pint.set_application_registry(ureg)

__default_preferred_units = [
    ureg.meter,
    ureg.second,
    ureg.kilogram,
    ureg.ampere,
    ureg.kelvin,
    ureg.mole,
    ureg.candela,
    ureg.radian,
    ureg.joule,
    ureg.watt,
    ureg.tesla,
    ureg.hertz,
    ureg.newton,
]

ureg.default_preferred_units = __default_preferred_units

DEFAULT_FORMAT = ".4g"
MULTIPLICATION_OPERATOR = "\\times"
AUTO_TRUNCATE_LENGTH = 6
USE_SIUNITX = False
USE_EXP_FOR_EXPONENTIAL = False
USE_ARC_FOR_INVERSE_TRIG = False
ARRAY_INDEX_SEPARATE = False
ARRAY_INDEX_BRACKET_TYPE = "square"


@pint.register_unit_format("T")
def format_unit_simple(unit, registry, **options):
    out = []
    for u, p in unit.items():
        u = f"{ureg.parse_units(u):~}"
        u = (
            u.replace("%", "\\%")
            .replace("°", "^{\\circ}")
            .replace("deg", "^{\\circ}")
            .replace("μ", "\\mu")
        )
        if p != 1:
            p = str(int(p)) if float(p).is_integer() else str(float(p))
            out.append(f"\\mathrm{{{u}}}^{{{p}}}")
        else:
            out.append(f"\\mathrm{{{u}}}")
    return "\\,".join(out)


class Token(ABC):
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

    # We'll use __matmul__ and __rmatmul__ for explicit multiplication

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
    
    def add(self, other: "Token") -> "Addition":
        return Addition(self, other)
    
    def plus(self, other: "Token") -> "Addition":
        return Addition(self, other)
    
    def subtract(self, other: "Token") -> "Subtraction":
        return Subtraction(self, other)
    
    def minus(self, other: "Token") -> "Subtraction":
        return Subtraction(self, other)
    
    def multiply(self, other: "Token") -> "Multiplication":
        return Multiplication(self, other)
    
    def times(self, other: "Token") -> "Multiplication":
        return Multiplication(self, other)
    
    def divide(self, other: "Token") -> "Division":
        return Division(self, other)
    
    def power(self, other: "Token") -> "Power":
        return Power(self, other)
    
    def index(self, other: "Token") -> "Index":
        return Index(self, other)

    def equals(self, other):
        return Equality(self, other)

    def less_than(self, other):
        return LessThan(self, other)
    
    def lt(self, other):
        return LessThan(self, other)

    def greater_than(self, other):
        return GreaterThan(self, other)
    
    def gt(self, other):
        return GreaterThan(self, other)

    def less_than_or_equal(self, other):
        return LessThanOrEqual(self, other)

    def leq(self, other):
        return LessThanOrEqual(self, other)

    def greater_than_or_equal(self, other):
        return GreaterThanOrEqual(self, other)

    def geq(self, other):
        return GreaterThanOrEqual(self, other)

    def not_equal(self, other):
        return NotEqual(self, other)

    def neq(self, other):
        return NotEqual(self, other)

    def approximately(self, other):
        return Approximation(self, other)

    def approx(self, other):
        return Approximation(self, other)

    def equivalent(self, other):
        return Equivalence(self, other)

    def equiv(self, other):
        return Equivalence(self, other)

    def tends_to(self, other):
        return Tends(self, other)

    def integral(self, lower: Any = None, upper: Any = None, variable: Any = None):
        return Integral(self, lower, upper, variable)

    def indefinite_integral(self, variable: Any = None):
        return Integral(self, variable=variable)

    def definite_integral(
        self, lower: Any = None, upper: Any = None, variable: Any = None
    ):
        return Integral(self, lower, upper, variable)

    def derivative(self, variable: Any, order: int = 1, as_operator: bool = False):
        return Derivative(self, variable, order, as_operator)

    def partial_derivative(
        self,
        *denominator_expr: Any,
        order: int | Any = 1,
        as_operator: bool = False,
    ):
        return PartialDerivative(
            self, *denominator_expr, order=order, as_operator=as_operator
        )

    def sqrt(self):
        return NthRoot(self, 2)

    def cbrt(self):
        return NthRoot(self, 3)

    def root(self, n: int = 2):
        return NthRoot(self, n)

    def abs(self):
        return AbsoluteValue(self)

    def sin(self):
        return Sine(self)

    def cos(self):
        return Cosine(self)

    def tan(self):
        return Tangent(self)

    def arcsin(self):
        return ArcSine(self)

    def arccos(self):
        return ArcCosine(self)

    def arctan(self):
        return ArcTangent(self)

    def sinh(self):
        return HyperbolicSine(self)

    def cosh(self):
        return HyperbolicCosine(self)

    def tanh(self):
        return HyperbolicTangent(self)

    def arcsinh(self):
        return HyperbolicArcSine(self)

    def arccosh(self):
        return HyperbolicArcCosine(self)

    def arctanh(self):
        return HyperbolicArcTangent(self)

    def log(self, base: int | float | Any = 10):
        return Logarithm(self, base)

    def ln(self):
        return NaturalLogarithm(self)

    def exponential(self, use_exp: Optional[bool] = None):
        return Exponential(self, use_exp)

    def exp(self, use_exp: Optional[bool] = None):
        return Exponential(self, use_exp)

    def dot(self):
        return dot(self)

    def ddot(self):
        return ddot(self)

    def hat(self):
        return hat(self)

    def bar(self):
        return bar(self)

    def vec(self):
        return vec(self)

    def underline(self):
        return underline(self)

    def tilde(self):
        return tilde(self)

    def widehat(self):
        return widehat(self)

    def widebar(self):
        return widebar(self)

    def overline(self):
        return overline(self)

    def at(self, other):
        return Index(MixedBracket(".", "|", self, scale=True), other)

    def prime(self):
        return Power(self, Macro("prime"))

    def pr(self):
        return Power(self, Macro("prime"))
    
    def array_index(self, *indices: Any, separate: Optional[bool] = None, bracket_type: Optional[str] = None):
        return ArrayIndex(self, *indices, separate=separate, bracket_type=bracket_type)

class Literal(Token):
    def __init__(self, value: str | float) -> "Literal":
        """Contains a string or float to handle its behaviour for typsetting.

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
    def __init__(self, value: str | float) -> "DimensionedLiteral":
        """Contains a string or float to handle its behaviour for typsetting. This differs from a Literal in that it is assumed to also contain units, and so some operators may treat it differently for bracketing purposes.

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


__unit_prefixes = [
    "quecto",
    "deca",
    "ronto",
    "hecto",
    "yocto",
    "kilo",
    "zepto",
    "mega",
    "atto",
    "giga",
    "femto",
    "tera",
    "pico",
    "peta",
    "nano",
    "exa",
    "micro",
    "zetta",
    "milli",
    "yotta",
    "centi",
    "ronna",
    "deci",
    "quetta",
]


def parse_unit(unit: pint.Unit | str) -> pint.Unit:
    """Parses a unit string into a pint.Unit object. The unit string may be in siunitx syntax (`\meter\per\second\squared`), written fully (meter per second squared), or abbreviated (`m/s^2` or `m s^-2`).)

    Parameters
    ----------
    unit : pint.Unit | str
        The unit to be parsed. This may be in siunitx format (e.g. `\meter\per\second\squared`), written fully (meter per second squared), or abbreviated (m/s^2 or m s^-2).

    Returns
    -------
    pint.Unit
        The parsed unit object.

    Raises
    ------
    TypeError
        If the unit is not a pint.Unit or str.
    """
    if isinstance(unit, pint.Unit):
        return unit
    if not isinstance(unit, str):
        raise TypeError(f"Expected pint.Unit or str, got {type(unit)}")
    # unit could be in siunitx format. Check for backslashes:
    if "\\" in unit:
        # this is (probably) a siunitx unit
        # pint expects centimeter, we will receive \centi\meter
        # replace \{prefix}\{unit} with {prefix}{unit}
        # replace backslash with space
        # check if it starts with "per " -- we need to handle this separately
        for prefix in __unit_prefixes:
            unit = re.sub(rf"\\{prefix}\s*\\", prefix, unit)
        unit = unit.replace("\\", " ")
        if unit.startswith("per "):
            unit = unit[4:]
            return 1 / ureg.parse_units(unit)
        return ureg.parse_units(unit)
    return ureg.parse_units(unit)


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
            The argument to the macro or environment. This can be a dictionary of key-value pairs, in which case they will be formatted as key=value. Nested dictionaries are not currently supported.
        is_optional : bool, optional
            If True, the argument will be rendered as optional, using square brackets instead of braces. Default False
        in_expl3 : bool, optional
            If True, the contents of the argument will be prepared to be used in expl3 (LaTeX3) syntax, with spaces being replaced by `~`. Default False
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
            return f"{open_delim}{', '.join([f'{key}={value}' for key, value in self.arg.items()])}{close_delim}"

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
        """A LaTeX macro, optionally with arguments.

        Parameters
        ----------
        name : str
            The name of the macro. For example, `Macro("LaTeX")` would render as `\LaTeX`.
        arguments : Tuple[Argument]
            A number of arguments for the macro. If a string, this will be converted to an `Argument` object. If a tuple, the first element should be the argument, and the second a boolean indicating whether it is optional. If an `Argument` object, it will be used as is.
        in_expl3 : bool, optional
            If True, the contents of any arguments will be prepared to be used in expl3 (LaTeX3) syntax, with spaces being replaced by `~`. Default False
        """
        self.name = name
        self.arguments = arguments
        self.in_expl3 = in_expl3

    def __str__(self) -> str:
        out = "\\" + self.name

        for arg in self.arguments:
            if isinstance(arg, tuple):
                out += Argument(arg[1], arg[0], self.in_expl3).__str__()
            else:
                out += Argument(arg, self.in_expl3).__str__()

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
            The name of the environment. For example, `Environment("document", "content")` would render as `\begin{document} content \end{document}`.
        arguments : str | Tuple[str, bool] | Argument, optional
            A number of arguments for the environment. If a string, this will be converted to an `Argument` object. If a tuple, the first element should be the argument, and the second a boolean indicating whether it is optional. If an `Argument` object, it will be used as is.
        content : str | Token | List[Token], optional
            The content of the environment. This can be a string, a single `Token` object, or a list of `Token` objects. If a list, the contents will be concatenated. Default None
        in_expl3 : bool, optional
            If True, the contents of any arguments will be prepared to be used in expl3 (LaTeX3) syntax, with spaces being replaced by `~`. Default False
        """
        self.name = name
        self.arguments = arguments
        self.content = content
        self.in_expl3 = in_expl3

    def __str__(self) -> str:
        out = Macro(
            "begin", self.name, *self.arguments, in_expl3=self.in_expl3
        ).__str__()
        if isinstance(self.content, (list, tuple)):
            out += "".join([str(expr) for expr in self.content])
        else:
            out += str(self.content)
        out += Macro("end", self.name).__str__()
        return out


class Quantity(CallableToken):
    def __init__(
        self,
        value: float,
        fmt: Optional[str] = None,
        unit: Optional[pint.Unit | str] = None,
    ) -> "Quantity":
        """A quantity with a value and unit.

        Parameters
        ----------
        value : float
            The value of the quantity.
        fmt : Optional[str], optional
            The format to use when rendering the quantity. If `fmt = ''`, no format specifier will be used. If None, the default format will be used. Default None
        unit : Optional[pint.Unit  |  str], optional
            The unit of the quantity. This can be a pint.Unit object, a string in siunitx format (e.g. `\meter\per\second\squared`), written fully (meter per second squared), or abbreviated (m/s^2 or m s^-2). If None, the value will be assumed to be dimensionless, unless a unit is specified later. Default None

        Raises
        ------
        ValueError
            If the value is a Token with a value that is a Token with a value that is a Token with a value... etc.
        ValueError
            If the value is a pint.Quantity (which already has a unit) and the unit is specified separately, but the units are incompatible.
        """
        # this might not be necessary --  we'll see. We might need to track the
        # initial value so that we can always access the magnitude in the
        # original units.
        i = 0
        while (
            isinstance(value, Token) and hasattr(value, "value") and i < 100
        ):  # this is a bit of a hack
            value = value.value
            i += 1
        if i == 100:
            raise ValueError(
                "Encountered seemingly infinitely nested expressions when creating Quantity"
            )
        self._initial_value = value
        self._initial_unit = unit
        self.fmt = fmt
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
                # self._value = self._initial_value * self._unit
                self._value = ureg.Quantity(self._initial_value, self._unit)
        elif isinstance(self._initial_value, pint.Quantity):
            self._initial_value = self._initial_value.to_preferred()
            self._unit = self._initial_value.units
            self._value = self._initial_value
        else:
            self._unit = None
            self._value = self._initial_value

    @property
    def value(self) -> pint.Quantity:
        return self._value

    @property
    def unit(self) -> pint.Unit:
        return self._unit

    @unit.setter
    def unit(self, unit: pint.Unit | str):
        if self._unit is None:
            self._unit = parse_unit(unit)
            self.value.unit = self._unit
            return
        try:
            self._value = self._value.to(parse_unit(unit))
            self._unit = self._value.units
        except pint.DimensionalityError:
            raise ValueError(f"Cannot convert {self._unit} to {unit}")
        # Otherwise, units are the same so we don't need to do anything

    @value.setter
    def value(self, value: float | pint.Quantity):
        if isinstance(value, pint.Quantity):
            self._unit = value.units
            self._value = value
            return
        self._initial_value = value
        if self._unit is not None:
            # self._value = value * self._unit
            self._value = ureg.Quantity(value, self._unit)
        else:
            self._value = value

    @property
    def fmt(self) -> str:
        return self._fmt

    @fmt.setter
    def fmt(self, fmt: str):
        self._fmt = fmt

    def __call__(
        self, fmt: Optional[str] = None, unit: Optional[pint.Unit | str] = None
    ) -> Literal:
        """Returns a Token representing the quantity, formatted as specified.

        Parameters
        ----------
        fmt : Optional[str], optional
            The format specifier to use when rendering the quantity. If None, the format specifier provided when the Quantity was created will be used. If that is also None, the default format specifier will be used. If `fmt = ''`, no format specifier will be used. Default None
        unit : Optional[pint.Unit  |  str], optional
            The unit to use when rendering the quantity. This can be a pint.Unit object, a string in siunitx format (e.g. `\meter\per\second\squared`), written fully (meter per second squared), or abbreviated (m/s^2 or m s^-2). If this unit is provided and the Quantity was created with a unit, the Quantity will be converted to this unit if possible. If None, the Quantity will be rendered in its current unit. If `unit = ''`, the Quantity will be rendered without a unit. Default None

        Returns
        -------
        Literal
            A Literal object containing the formatted quantity.
        """
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


def format_value(
    value: float | pint.Quantity,
    fmt: Optional[str] = None,
    unit: Optional[pint.Unit | str] = None,
) -> Tuple[str, bool]:
    """Formats a value with an optional unit.

    Parameters
    ----------
    value : float | pint.Quantity
        The value to be formatted.
    fmt : Optional[str], optional
        The format specifier to use when rendering the value. If None, the default format specifier will be used. If `fmt = ''`, no format specifier will be used. Default None
    unit : Optional[pint.Unit  |  str], optional
        The unit to use when rendering the value. This can be a pint.Unit object, a string in siunitx format (e.g. `\meter\per\second\squared`), written fully (meter per second squared), or abbreviated (m/s^2 or m s^-2). If None, the value will be assumed to be dimensionless. If `unit = ''`, the value will be rendered without a unit. Default None

    Returns
    -------
    Tuple[str, bool]
        A tuple containing the formatted value and a boolean indicating whether the value has units.

    Raises
    ------
    ValueError
        If the unit is not a pint.Unit or str.
    ValueError
        If the unit is specified and the value is a pint.Quantity with units, but the units are incompatible.
    """
    # unit = None -> use the unit of the value
    # unit = "" -> no unit
    # Returns the formatted value and whether or not it has units (for bracketing purposes)
    if isinstance(value, pint.Quantity):
        if unit is not None and unit != value.units and unit != "":
            if value.dimensionless and not value.units == ureg.percent:
                value = value * parse_unit(unit)
            else:
                try:
                    value = value.to(parse_unit(unit))
                except pint.DimensionalityError:
                    raise ValueError(f"Cannot convert {value.units} to {unit}")
        if unit == "":
            value, unit = value.magnitude, None
        else:
            value, unit = value.magnitude, value.units
    if isinstance(unit, str):
        if unit == "":
            unit = None
        else:
            try:
                unit = parse_unit(unit)
            except Exception:
                raise ValueError(f"Invalid unit: {unit}")
    if fmt is None:
        fmt = DEFAULT_FORMAT
    if fmt is not None:
        # TODO: fractional format
        print_value = f"{value:{fmt}}"
    else:
        print_value = f"{value}"
    if "e" in print_value:
        print_value, exponent = print_value.split("e")
        exponent = str(int(exponent))
    elif "E" in print_value:
        print_value, exponent = print_value.split("E")
        exponent = str(int(exponent))
    else:
        exponent = ""
    if exponent == "0":
        exponent = ""
    if fmt is None or "." not in fmt:
        print_value = __truncate_zeros(print_value)
    if exponent:
        if unit is None or unit.dimensionless and unit != ureg.percent:
            return f"{print_value} \\times 10^{{{exponent}}}", False
        return (
            f"{print_value} \\times 10^{{{exponent}}}"
            + (f"\\ {format_unit(unit, si = USE_SIUNITX)}" if unit else ""),
            True,
        )
    if unit is None or unit.dimensionless and unit != ureg.percent:
        return print_value, False
    return (
        print_value + (f"\\ {format_unit(unit, si = USE_SIUNITX)}" if unit else ""),
        True,
    )


def si(
    value: float | pint.Quantity | str,
    fmt: Optional[str] = None,
    unit: Optional[pint.Unit | str] = None,
    in_math_mode: bool = False,
    in_unit: Optional[pint.Unit | str] = None,
    # exp_only: bool = False,
) -> str:
    """Formats a value with SI units.

    Parameters
    ----------
    value : float | pint.Quantity | str
        The value to be formatted. If a string, it will be converted to a float if possible, or rendered as is if not.
    fmt : Optional[str], optional
        The format specifier to use when rendering the value. If None, the default format specifier will be used. If `fmt = ''`, no format specifier will be used. Default None
    unit : Optional[pint.Unit  |  str], optional
        The unit to use when rendering the value. This can be a pint.Unit object, a string in siunitx format (e.g. `\meter\per\second\squared`), written fully (meter per second squared), or abbreviated (m/s^2 or m s^-2). If None, the value will be assumed to be dimensionless. If `unit = ''`, the value will be rendered without a unit. Default None
    in_math_mode : bool, optional
        If True, it is assumed that the function is called from inside math mode. If False, math mode delimiters (`$`) will be added. Default False
    in_unit: Optional[pint.Unit  |  str], optional
        If provided, the `value` is interpreted to be in `unit`, then converted to `in_unit` before formatting. For example, `si(1, unit = "kg", in_unit = "g")` would result in `1000 g`. Default None

    Returns
    -------
    str
        The formatted value with SI units.
    """
    # TODO:
    # exp_only : bool, optional
    #     If True, and the value is some power of 10, the value will be rendered without the significand. I.e, if the value is 1e9, this would be rendered as $10^9$, rather than $1 \\times 10^9$. Default False
    parse_value = True
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            parse_value = False
    if in_unit is not None:
        if unit is None and not isinstance(value, pint.Quantity):
            # If no initial unit is provided, this is probably a mis-use of the arguments.
            return si(value, fmt=fmt, unit=in_unit, in_math_mode=in_math_mode)
        if not parse_value:
            raise ValueError(
                f"Cannot perform unit conversion on non-numeric value (str) `{value}`"
            )
        in_unit = parse_unit(in_unit)
        if isinstance(value, pint.Quantity):
            return si(value, fmt=fmt, unit=in_unit, in_math_mode=in_math_mode)
        value = pint.Quantity(value, parse_unit(unit))
        return si(value, fmt=fmt, unit=in_unit, in_math_mode=in_math_mode)
    if in_math_mode:
        if parse_value:
            return as_token(format_value(value, fmt, unit)[0])
        if unit is None:
            return as_token(value)
        return as_token(value) * space * as_token(format_unit(parse_unit(unit)))
    if parse_value:
        return "$" + "\\ " + format_value(value, fmt, unit)[0] + "$"
    if unit is None:
        return "$" + value + "$"
    return "$" + value + "\\ " + format_unit(parse_unit(unit)) + "$"


def __truncate_zeros(value: str) -> str:
    if "." in value:
        integer, decimal = value.split(".")
        if len(decimal) > AUTO_TRUNCATE_LENGTH:
            decimal = int(decimal[: AUTO_TRUNCATE_LENGTH + 1])
            # round to nearest 10
            decimal = round(decimal, -1)
            # check if we've rolled over to a new integer
            if len(str(decimal)) > AUTO_TRUNCATE_LENGTH:
                integer = str(int(integer) + 1)
                decimal = ""  # decimal will always be 0 at this point
        # remove trailing zeros
        decimal = decimal.rstrip("0")
        if decimal:
            return f"{integer}.{decimal}"
        return integer
    return value


def format_unit(unit: pint.Unit, si: bool = False) -> str:
    """Formats a pint.Unit object.

    Parameters
    ----------
    unit : pint.Unit
        The unit to be formatted.
    si : bool, optional
        If True, the unit will be formatted using siunitx syntax. Otherwise, the unit will be formatted directly using `\mathrm`. Default False

    Returns
    -------
    str
        The formatted unit.
    """
    if si:
        return f"{unit:Lx}"
    return f"{unit:T}"


def unit(unit: str | pint.Unit, in_math_mode: bool = False) -> str:
    """Formats a unit.

    Parameters
    ----------
    unit : str | pint.Unit
        The unit to be formatted. This can be a pint.Unit object, a string in siunitx format (e.g. `\meter\per\second\squared`), written fully (`meter per second squared`), or abbreviated (`m/s^2` or `m s^-2`).
    in_math_mode : bool, optional
        If True, it is assumed that the function is called from inside math mode. If False, math mode delimiters (`$`) will be added. Default False

    Returns
    -------
    str
        The formatted unit.
    """
    if in_math_mode:
        return format_unit(parse_unit(unit))
    return "$" + format_unit(parse_unit(unit)) + "$"


# def format_si_unit(units: str, html: bool = False) -> str:
#     units = units.strip()
#     if units.startswith("per "):
#         parsed = 1 / ureg.parse_expression(units[4:])
#     else:
#         parsed = ureg.parse_expression(units)
#     if html:
#         output = f"{parsed.units:~Hs}"
#         # output = re.sub(r"\bdeg\b", "&deg;", output)
#         output = output.replace("deg", "&deg;")
#         return output
#     output = f"{parsed.units:~Ls}"
#     output = re.sub(r"\bdeg\b", r"^{\\circ}", output)
#     return output


class Variable(Quantity):
    def __init__(
        self,
        name: str,
        value: float,
        fmt: Optional[str] = None,
        unit: Optional[pint.Unit | str] = None,
    ) -> "Variable":
        """A variable with a name, value, and optional unit and format specifier.

        Parameters
        ----------
        name : str
            The name of the variable. This will be used when rendering the variable directly.
        value : float
            The value of the variable. This will be used when the variable is called as a function.
        fmt : Optional[str], optional
            The format specifier to use when rendering the variable. If None, the default format specifier will be used. If `fmt = ''`, no format specifier will be used. Default None
        unit : Optional[pint.Unit  |  str], optional
            The unit of the variable. This can be a pint.Unit object, a string in siunitx format (e.g. `\meter\per\second\squared`), written fully (meter per second squared), or abbreviated (m/s^2 or m s^-2). If None, the value will be assumed to be dimensionless. Default None
        """
        super().__init__(value, fmt, unit)
        self.name = Literal(name)

    def __str__(self) -> str:
        return self.name.__str__()


def as_token(value: Token | str | float | List | Tuple | Set | pint.Quantity) -> Token:
    """Converts a value to a Token or subclass.

    Parameters
    ----------
    value : Token | str | float | List | Tuple | Set | pint.Quantity
        The value to be converted. If this is an iterable (tuple, list, set), the elements will be converted to Tokens, and if there is only a single element it will be encased in the appropriate brackets.

    Returns
    -------
    Token
        The converted value. This can be a Token, Literal, Quantity, SquareBracket, Bracket, or CurlyBracket.

    Raises
    ------
    TypeError
        If the value cannot be converted to a Token.
    """
    if isinstance(value, Token):
        return value
    if isinstance(value, pint.Quantity):
        return Quantity(value.magnitude, unit=value.units)
    if isinstance(value, str):
        if value.isnumeric():
            value = float(value)
            # if it's an integer, convert to int
            if value.is_integer():
                value = int(value)
            return Quantity(value)
        return Literal(value)
    if isinstance(value, float):
        return Quantity(value)
    if isinstance(value, int):
        return Quantity(value, fmt="d")
    if isinstance(value, list):
        return SquareBracket(*[as_token(v) for v in value], scale=True)
    if isinstance(value, tuple):
        return Bracket(*[as_token(v) for v in value], scale=True)
    if isinstance(value, set):
        return CurlyBracket(*[as_token(v) for v in value], scale=True)

    raise TypeError(f"Expected Token, str, or float, got {type(value)}")


symbol = as_token
sym = as_token


class _UnaryOperator(Quantity, ABC):
    def __init__(self, value: CallableToken | str | float) -> "_UnaryOperator":
        self.right = as_token(value)
        self.symbol = ""
        self._value = None

    def __str__(self) -> str:
        return f"{self.symbol}{{{self.right}}}"

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        value = self.value
        if isinstance(value, pint.Quantity):
            return Quantity(value.magnitude, unit=value.units)(*args, **kwargs)
        return Quantity(value)(*args, **kwargs)

    @abstractmethod
    def _operation(self, value: CallableToken) -> Any:
        pass

    @property
    def value(self) -> Any:
        if self._value is None:
            self._value = self._operation(self.right)
        return self._value

    @property
    def unit(self) -> pint.Unit:
        if isinstance(self.value, Quantity):
            return self.value.unit
        elif isinstance(self.value, pint.Quantity):
            return self.value.units
        return None

    @unit.setter
    def unit(self, unit: pint.Unit | str):
        if isinstance(self.value, Quantity):
            self.value.unit = unit
        elif isinstance(self.value, pint.Quantity):
            self._value = self.value.to(unit)
        else:
            raise ValueError(
                f"Cannot set unit of non-Quantity of type {str(type(self.value)).replace('<', '').replace('>', '')}"
            )

    def as_quantity(self) -> Quantity:
        return Quantity(self.value)


class Negation(_UnaryOperator):
    def __init__(self, value: CallableToken | str | float) -> "Negation":
        """Negates a value, such as `-a`.

        Parameters
        ----------
        value : CallableToken | str | float
            The value to be negated
        """
        super().__init__(value)
        self.symbol = "-"

    def _operation(self, value: CallableToken) -> Any:
        return -value.value


class Positive(_UnaryOperator):
    def __init__(self, value: CallableToken | str | float) -> "Positive":
        """Returns the positive value of a quantity, such as `+a`. This is numerically equivalent to `a`, and only differs in rendering. It is *not* equivalent to `abs(a)`. Use `absolute(a)` for the absolute value.

        Parameters
        ----------
        value : CallableToken | str | float
            The value.
        """
        super().__init__(value)
        self.symbol = "+"

    def _operation(self, value: CallableToken) -> Any:
        return value.value


class _BinaryOperator(CallableToken, ABC):
    def __init__(
        self,
        left: CallableToken | str | float,
        right: CallableToken | str | float,
    ) -> "_BinaryOperator":
        self.left = as_token(left)
        self.right = as_token(right)
        self.symbol = ""
        self.precedence = 0  # we'll use this to track if we need to add parentheses
        self.group_left = False
        self.group_right = False
        # super().__init__(self.value)
        self._value = None

    def __str__(self) -> str:
        left = f"{{{self.left}}}" if self.group_left else f"{self.left}"
        right = f"{{{self.right}}}" if self.group_right else f"{self.right}"
        return f"{left} {self.symbol} {right}"

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        """Render the value (potentially with units) of the operation.

        Returns
        -------
        Literal
            The rendered value.
        """
        value = self.value
        if isinstance(value, pint.Quantity):
            return Quantity(value.magnitude, unit=value.units)(*args, **kwargs)
        return Quantity(value)(*args, **kwargs)

    @abstractmethod
    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        pass

    # TODO: Tidy this up, and apply to other classes (UnaryOperator)

    @property
    def value(self) -> Any:
        if self._value is None:
            self._value = self._operation(self.left, self.right)
        return self._value

    @property
    def unit(self) -> pint.Unit:
        if isinstance(self.value, Quantity):
            return self.value.unit
        elif isinstance(self.value, pint.Quantity):
            return self.value.units
        return None

    @unit.setter
    def unit(self, unit: pint.Unit | str):
        if isinstance(self.value, Quantity):
            self.value.unit = unit
        elif isinstance(self.value, pint.Quantity):
            self._value = self.value.to(unit)
        else:
            raise ValueError(
                f"Cannot set unit of non-Quantity of type {str(type(self.value)).replace('<', '').replace('>', '')}"
            )

    def as_quantity(self) -> Quantity:
        """Convert the operation object to a Quantity with the value and units of the operation.

        Returns
        -------
        Quantity
            The Quantity object with the value and units of the operation.
        """
        return Quantity(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __int__(self) -> int:
        return int(self.value)


class Addition(_BinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "Addition":
        """Adds two values together, such as `a + b`.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "+"
        self.precedence = 1

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value + right.value


class Subtraction(_BinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "Subtraction":
        """Subtracts one value from another, such as `a - b`.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "-"
        self.precedence = 1

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value - right.value


class Multiplication(_BinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "Multiplication":
        """Multiplies two values together, such as `a * b`. This is rendered as `ab`.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = ""  # multiplication is implicit, Multiplication(a, b) -> ab. Use Times(a, b) to get a \times b
        self.precedence = 2

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value * right.value


class Times(_BinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "Times":
        """Multiplies two values together, such as `a * b`. This is rendered as `a \\times b` (or `a \\cdot b` etc. depending on the value of `MULTIPLICATION_OPERATOR`).

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = MULTIPLICATION_OPERATOR
        self.precedence = 2

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value * right.value


class Division(_BinaryOperator):
    def __init__(
        self,
        left: CallableToken | str | float,
        right: CallableToken | str | float,
        display_mode: bool = False,
    ) -> "Division":
        """Divides one value by another, such as `a / b`. This is rendered as `\\frac{a}{b}`, or `\\dfrac{a}{b}` if `display_mode = True`.

        Parameters
        ----------
        left : CallableToken | str | float
            The numerator.
        right : CallableToken | str | float
            The denominator.
        display_mode : bool, optional
            If True, the division will be rendered as a display fraction regardless of the context, using `\\dfrac` instead of `\\frac`. Default False
        """
        super().__init__(left, right)
        if (
            display_mode
        ):  # these will not format properly -- we're overriding the __str__ function anyway.
            self.symbol = "\\dfrac"
        else:
            self.symbol = "\\frac"
        self.precedence = 2

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value / right.value

    def __str__(self) -> str:
        return f"{self.symbol}{{{self.left}}}{{{self.right}}}"


class Power(_BinaryOperator):
    def __init__(
        self,
        left: CallableToken | str | float,
        right: CallableToken | str | float,
    ) -> "Power":
        """Raises one value to the power of another, such as `a ** b`. This is rendered as `a^b`. Special behaviour occurs if the left operand is an Index object (to allow constructs like `a_i^2` instead of `{a_i}^2`), or if the left operand is a DimensionedLiteral (to allow constructs like `(2 m)^2` instead of `2 m^2`).

        Parameters
        ----------
        left : CallableToken | str | float
            The base.
        right : CallableToken | str | float
            The exponent.
        """
        super().__init__(left, right)
        self.symbol = "^"
        self.precedence = 3
        self.group_right = True
        if not isinstance(left, Index):
            self.group_left = True
        if isinstance(self.left, DimensionedLiteral):
            self.left = Bracket(
                self.left, scale=True
            )  # Should this be in the string conversion rather than here? Would mean changes to _BinaryOperator or a separate __str__ for Power.

    def _operation(self, left: CallableToken, right: CallableToken) -> Any:
        return left.value**right.value


class Index(_BinaryOperator):
    def __init__(
        self,
        left: CallableToken | str | float,
        right: CallableToken | str | float,
    ) -> "Index":
        """Indexes one value with another, such as `a_i`. This is rendered as `a_i`. Special behaviour occurs if the left operand is a Power object (to allow constructs like `a^2_i` instead of `{a^2}_i`).

        Parameters
        ----------
        left : CallableToken | str | float
            The base.
        right : CallableToken | str | float
            The index.
        """
        super().__init__(left, right)
        self.symbol = "_"
        self.precedence = 3
        self.group_right = True
        if not isinstance(left, Power):
            self.group_left = True

    def _operation(self, left: CallableToken, right: CallableToken) -> None:
        pass  # This is not a real operation, and only exists for simple formatting


class Concatenation(Token):
    # non callable
    def __init__(self, *args: CallableToken) -> "Concatenation":
        """Concatenates a number of values together, such as `Concatenation(a, b, c)` --> `abc`."""
        self.args = args

    def __str__(self) -> str:
        return " ".join(str(arg) for arg in self.args)


class _Container(CallableToken, ABC):
    def __init__(self, *children: str | float | Token) -> "_Container":
        self.children = [as_token(child) for child in children]

    @abstractmethod
    def __str__(self) -> str:
        pass

    @property
    def value(self) -> Quantity | None:
        if len(self.children) == 1:
            return self.children[0].value
        return None

    def __getitem__(self, index: int) -> Token:
        # We want this to actually act like an array index, not a subscript
        return self.children[index]

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        if len(self) == 1:
            return self.children[0](*args, **kwargs)
        raise ValueError(f"Cannot call a container with multiple {len(self)} children")

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self):
        return iter(self.children)


class Collection(_Container):
    # Basically a container, but with a str method with no delimiters
    def __str__(self) -> str:
        return " ".join(str(child) for child in self.children)


class Sequence(_Container):
    def __str__(self) -> str:
        return ", ".join(str(child) for child in self.children)


class Bracket(_Container):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> "Bracket":
        """A bracketed expression, such as `(a + b)`.

        Parameters
        ----------
        scale : bool, optional
            If True, the brackets will be scaled to fit the contents. Default False
        """
        super().__init__(*children)
        self.scale = scale
        self.left_bracket = "("
        self.right_bracket = ")"

    def __str__(self) -> str:
        scale_left, scale_right = ("\\left", "\\right") if self.scale else ("", "")
        return f"{scale_left}{self.left_bracket} {', '.join(str(child) for child in self.children)} {scale_right}{self.right_bracket}"


class SquareBracket(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> "SquareBracket":
        """A square bracketed expression, such as `[a + b]`.

        Parameters
        ----------
        scale : bool, optional
            If True, the brackets will be scaled to fit the contents. Default False
        """
        super().__init__(*children, scale=scale)
        self.left_bracket = "["
        self.right_bracket = "]"


class CurlyBracket(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> "CurlyBracket":
        """A curly bracketed/braced expression, such as `{a + b}`.

        Parameters
        ----------
        scale : bool, optional
            If True, the brackets will be scaled to fit the contents. Default False
        """
        super().__init__(*children, scale=scale)
        self.left_bracket = "\\lbrace"
        self.right_bracket = "\\rbrace"


class AngleBracket(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> "AngleBracket":
        """An angle bracketed expression, such as `<a + b>`.

        Parameters
        ----------
        scale : bool, optional
            If True, the brackets will be scaled to fit the contents. Default False
        """
        super().__init__(*children, scale=scale)
        self.left_bracket = "\\langle"
        self.right_bracket = "\\rangle"


class AbsoluteValue(Bracket):
    def __init__(
        self, *children: str | float | Token, scale: bool = False
    ) -> "AbsoluteValue":
        """An absolute value expression, such as `|a + b|`.

        Parameters
        ----------
        scale : bool, optional
            If True, the brackets will be scaled to fit the contents. Default False
        """
        super().__init__(*children, scale=scale)
        self.left_bracket = "|"
        self.right_bracket = "|"
        if self.value < 0:
            self._value = (
                -self.value
            )  # seems like the safest way to do this when value could be anything
        else:
            self._value = self.value

    # This one can actually be called!
    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        value = self._value

        if isinstance(value, pint.Quantity):
            return Quantity(value.magnitude, unit=value.units)(*args, **kwargs)
        return Quantity(value)(*args, **kwargs)


class MixedBracket(Bracket):
    __bracket_shorthands = {
        "<": "\\langle",
        ">": "\\rangle",
    }

    def __init__(
        self,
        left: str | Token,
        right: str | Token,
        *children: str | float | Token,
        scale: bool = False,
    ) -> "MixedBracket":
        """A mixed bracketed expression, such as `[0, 1)`.

        Parameters
        ----------
        left : str | Token
            The left bracket. "<" and ">" will be converted to "\\langle" and "\\rangle" respectively.
        right : str | Token
            The right bracket. "<" and ">" will be converted to "\\langle" and "\\rangle" respectively.
        scale : bool, optional
            If True, the brackets will be scaled to fit the contents. Default False
        """
        super().__init__(*children, scale=scale)
        self.left_bracket = self.__bracket_shorthands.get(left, left)
        self.right_bracket = self.__bracket_shorthands.get(right, right)


# TODO: Fully implement dirac notation with \mid, like <a|H|b>
# TODO: Implement a parser for this.


class ArrayIndex(Token):
    def __init__(
        self,
        array: str | Token,
        *index: str | Token,
        separate: Optional[bool] = None,
        bracket_type: Optional[str] = None,
    ):
        self.array = texttt(array) if isinstance(array, str) else as_token(array)
        self.index = [texttt(i) if isinstance(i, str) else as_token(i) for i in index]
        if separate is None:
            self.separate = ARRAY_INDEX_SEPARATE
        else:
            self.separate = separate
        if bracket_type is None:
            self.bracket_type = ARRAY_INDEX_BRACKET_TYPE
        else:
            self.bracket_type = bracket_type

    def __str__(self) -> str:
        output = [self.array]
        bracket_types = {
            "square": ("[", "]"),
            "curly": ("\\{", "\\}"),
            "angle": ("\\langle", "\\rangle"),
            "absolute": ("|", "|"),
            "round": ("(", ")"),
            "paren": ("(", ")"),
        }
        bracket_type = bracket_types.get(self.bracket_type, Bracket)
        bracket_type = (Macro("texttt", bracket_type[0]), Macro("texttt", bracket_type[1]))
        if self.separate:
            output.extend(bracket_type[0] & i & bracket_type[1] for i in self.index)
        else:
            output.append(bracket_type[0] & Sequence(*self.index) & bracket_type[1])
        return str(Concatenation(*output))


class _BooleanBinaryOperator(_BinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "_BooleanBinaryOperator":
        super().__init__(left, right)
        self.precedence = 1

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        value = self._operation(self.left, self.right)
        return Literal(str(value))

    @abstractmethod
    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        pass


class Equality(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "Equality":
        """Equality between two expressions, such as `a = b`. This is rendered as `a = b`, and its value is as expected; `True` if `a` is equal to `b`, `False` otherwise.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "="

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value == right.value


class LessThan(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "LessThan":
        """Inequality between two expressions, such as `a < b`. This is rendered as `a < b`, and its value is as expected; `True` if `a` is less than `b`, `False` otherwise.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "<"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value < right.value


class GreaterThan(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "GreaterThan":
        """Inequality between two expressions, such as `a > b`. This is rendered as `a > b`, and its value is as expected; `True` if `a` is greater than `b`, `False` otherwise.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = ">"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value > right.value


class LessThanOrEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "LessThanOrEqual":
        """Inequality between two expressions, such as `a <= b`. This is rendered as `a \\leq b`, and its value is as expected; `True` if `a` is less than or equal to `b`, `False` otherwise.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "\\leq"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value <= right.value


class GreaterThanOrEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "GreaterThanOrEqual":
        """Inequality between two expressions, such as `a >= b`. This is rendered as `a \\geq b`, and its value is as expected; `True` if `a` is greater than or equal to `b`, `False` otherwise.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "\\geq"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value >= right.value


class NotEqual(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "NotEqual":
        """Inequality between two expressions, such as `a != b`. This is rendered as `a \\neq b`, and its value is as expected; `True` if `a` is not equal to `b`, `False` otherwise.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "\\neq"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value != right.value


class Approximation(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "Approximation":
        """Approximate equality between two expressions. This is rendered as `a \\approx b`. Since approximate equality is not neatly defined, its value is equivalent to `a == b`.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "\\approx"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value == right.value


class Equivalence(_BooleanBinaryOperator):
    def __init__(
        self, left: CallableToken | str | float, right: CallableToken | str | float
    ) -> "Equivalence":
        """Logical equivalence between two expressions. This is rendered as `a \\equiv b`. Its value is evaluated identically to `a == b`.

        Parameters
        ----------
        left : CallableToken | str | float
            The left operand.
        right : CallableToken | str | float
            The right operand.
        """
        super().__init__(left, right)
        self.symbol = "\\equiv"

    def _operation(self, left: CallableToken, right: CallableToken) -> bool:
        return left.value == right.value


class Tends(Token):
    def __init__(self, variable: Token | Any, limit: Token | Any) -> "Tends":
        """A limit expression, such as `x \\to a`.

        Parameters
        ----------
        variable : Token | Any
            The variable, such as `x` in the example above.
        limit : Token | Any
            The limit of the variable, such as `a` in the example above.
        """
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
        """A mathematical expression with limits, such as an integral or summation.

        Parameters
        ----------
        function : Macro | Token | str
            The function to be applied, such as `int` for an integral or `sum` for a summation. If this is a string, it will be converted to a Macro object.
        expr : Token | Any
            The expression to which the function is applied, i.e. the integrand in an integral.
        lower : Token | Any, optional
            The lower limit of the expression, by default None
        upper : Token | Any, optional
            The upper limit of the expression, by default None
        suffix : Token | Any, optional
            A suffix to be added to the expression, such as `dx` in an integral, by default None
        """
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
        """An integral expression, such as `\\int_{a}^{b} f(x) dx`.

        Parameters
        ----------
        expr : Token | Any
            The integrand.
        lower : Token | Any, optional
            The lower limit of the integral, by default None
        upper : Token | Any, optional
            The upper limit of the integral, by default None
        variable : Token | Any, optional
            The variable of integration, such as `x` which will be rendered as `dx`, by default None
        """
        super().__init__(
            "int", expr, lower, upper, Macro(",") & Macro("mathrm", "d") & variable
        )


class Limit(LimitsExpression):
    def __init__(
        self, expr: Token | Any, variable: Token | Any = None, limit: Token | Any = None
    ):
        """A limit expression, such as `\\lim_{x \\to a} f(x)`.

        Parameters
        ----------
        expr : Token | Any
            The expression.
        variable : Token | Any, optional
            The variable, such as `x` in the example above, by default None
        limit : Token | Any, optional
            The limit of the variable, such as `a` in the example above, by default None
        """
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
        """A summation expression, such as `\\sum_{i = 0}^{n} a_i`.

        Parameters
        ----------
        expr : Token | Any
            The expression to be summed.
        lower : Token | Any, optional
            The lower limit of the summation, such as `0` in the example above, by default None
        variable : Token | Any, optional
            The variable of the summation, such as `i` in the example above, by default None
        upper : Token | Any, optional
            The upper limit of the summation, such as `n` in the example above, by default None
        """
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
        """
        A derivative expression, such as `\\frac{\\mathrm{d}^2 y}{\\mathrm{d} x^2}` or `\\frac{\\mathrm{d}}{\\mathrm{d} x} f(x)`.

        Parameters
        ----------
        numerator_expr : Token | Any
            The expression to be differentiated.
        denominator_expr : Token | Any
            The expression with respect to which the derivative is taken.
        order : int | Token | Any, optional
            The order of the derivative, by default 1 (which will not be rendered).
        as_operator : bool, optional
            If True, the derivative will be rendered as an operator acting on the numerator expression, i.e. `d/dx f(x)`, rather than `df(x)/dx`.
        """
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
        # Really this only inherits from Derivative to keep the hierarchy logical from a mathematical perspective. It actually doesn't share much with Derivative at all.
        """
        A partial derivative expression, such as `\\frac{\\partial^2 y}{\\partial x^2}` or `\\frac{\\partial}{\\partial x} f(x)`.

        Parameters
        ----------
        numerator_expr : Token | Any
            The expression to be differentiated.
        denominator_expr : Token | Any
            Any number of expressions with respect to which the derivative is taken. If `order` is numeric and greater than the number of expressions, the last expression will be repeated.
        order : int | Token | Any, optional
            The order of the derivative, by default 1 (which will not be rendered). If not provided, the number of denominator expressions will be used.
        as_operator : bool, optional
            If True, the derivative will be rendered as an operator acting on the numerator expression, i.e. `\\partial/\\partial x f(x)`, rather than `\\partial f(x)/\\partial x`.
        """
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

    def __str__(self):
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
            post = empty
        denominator = []
        for expr, order in self.denominator_expr_orders.items():
            if order == 1:
                denominator.append(self.derivative_operator & expr)
            else:
                denominator.append(self.derivative_operator & expr**order)

        return str(numerator / Collection(*denominator) & post)


class NthRoot(CallableToken):
    def __init__(
        self, value: Token | str | float, root: Token | str | float
    ) -> "NthRoot":
        """The nth root of a value, such as `\\sqrt{a}` or `\\sqrt[3]{a}`.

        Parameters
        ----------
        value : Token | str | float
            The value to be rooted.
        root : Token | str | float
            The order of the root. If this is 2, the root will be a square root (rendered with `\\sqrt`), if 3 it will be a cube root (rendered with `\\sqrt[3]`), etc.
        """
        self.value = as_token(value)
        self.root = as_token(root)

    def __str__(self) -> str:
        if self.root.value == 2:
            return f"\\sqrt{{{self.value}}}"
        return f"\\sqrt[{self.root}]{{{self.value}}}"

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        return Quantity(self.value.value ** (1 / self.root.value))(*args, **kwargs)


def sqrt(value: Token | str | float) -> NthRoot:
    """The square root of a value, such as `\\sqrt{a}`.

    Parameters
    ----------
    value : Token | str | float
        The value to be rooted.

    Returns
    -------
    NthRoot
        The square root of the value.
    """
    return NthRoot(value, 2)


def cbrt(value: Token | str | float) -> NthRoot:
    """The cube root of a value, such as `\\sqrt[3]{a}`.

    Parameters
    ----------
    value : Token | str | float
        The value to be rooted.

    Returns
    -------
    NthRoot
        The cube root of the value.
    """
    return NthRoot(value, 3)


class _TrigFunction(CallableToken, ABC):
    # Not all of these are actually trig functions, but behave the same for formatting purposes
    def __init__(
        self,
        name: str,
        expr: Token | str,
        power: Optional[Token | Any] = None,
        inverse: bool = False,
    ):
        self.name = name
        self.expr = as_token(expr)
        self.power = None if power is None else as_token(power)
        self.inverse = inverse

    def __str__(self) -> str:
        if self.inverse:
            if self.power is None:
                return str(
                    Collection(
                        Power(Macro(self.name), as_token(-1)),
                        Bracket(self.expr, scale=True),
                    )
                )
            return str(
                Power(
                    Bracket(
                        Collection(
                            Power(Macro(self.name), as_token(-1)),
                            Bracket(self.expr, scale=True),
                        )
                    ),
                    self.power,
                )
            )
        if self.power is None:
            return str(Collection(Macro(self.name), Bracket(self.expr, scale=True)))
        return str(
            Collection(
                Power(Macro(self.name), self.power), Bracket(self.expr, scale=True)
            )
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        value = self._operation(self.expr, self.power)
        if isinstance(value, pint.Quantity):
            return Quantity(value.magnitude, unit=value.units)(*args, **kwargs)
        return Quantity(value)(*args, **kwargs)

    @abstractmethod
    def _operation(self, expr: Token, power: Token) -> Any:
        pass


class Sine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "Sine":
        """The sine of an expression, optionally to some power, such as `\\sin^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the sine function.
        power : Optional[Token  |  Any], optional
            The power to which the sine is raised. Note that `power = -1` is *not* equivalent to `arcsin(a)`, but rather `1/sin(a)`. For the inverse sine function, use `ArcSine` instead. Default None (equivalent to 1)
        """
        super().__init__("sin", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.sin(expr.value) ** (1 if power is None else power.value)


class Cosine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "Cosine":
        """The cosine of an expression, optionally to some power, such as `\\cos^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the cosine function.
        power : Optional[Token  |  Any], optional
            The power to which the cosine is raised. Note that `power = -1` is *not* equivalent to `arccos(a)`, but rather `1/cos(a)`. For the inverse cosine function, use `ArcCosine` instead. Default None (equivalent to 1)
        """
        super().__init__("cos", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.cos(expr.value) ** (1 if power is None else power.value)


class Tangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "Tangent":
        """The tangent of an expression, optionally to some power, such as `\\tan^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the tangent function.
        power : Optional[Token  |  Any], optional
            The power to which the tangent is raised. Note that `power = -1` is *not* equivalent to `arctan(a)`, but rather `1/tan(a)`. For the inverse tangent function, use `ArcTangent` instead. Default None (equivalent to 1)
        """
        super().__init__("tan", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.tan(expr.value) ** (1 if power is None else power.value)


class ArcSine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "ArcSine":
        """The inverse sine of an expression, optionally to some power, such as `\\sin^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse sine function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse sine is raised. Default None (equivalent to 1)
        """
        super().__init__("sin", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.asin(expr.value) ** (1 if power is None else power.value)


class ArcCosine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "ArcCosine":
        """The inverse cosine of an expression, optionally to some power, such as `\\cos^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse cosine function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse cosine is raised. Default None (equivalent to 1)
        """
        super().__init__("cos", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.acos(expr.value) ** (1 if power is None else power.value)


class ArcTangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "ArcTangent":
        """The inverse tangent of an expression, optionally to some power, such as `\\tan^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse tangent function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse tangent is raised. Default None (equivalent to 1)
        """
        super().__init__("tan", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.atan(expr.value) ** (1 if power is None else power.value)


class Cosecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "Cosecant":
        """The cosecant of an expression, optionally to some power, such as `\\csc^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the cosecant function.
        power : Optional[Token  |  Any], optional
            The power to which the cosecant is raised. Note that `power = -1` is *not* equivalent to `arccsc(a)`, but rather `1/csc(a)`. For the inverse cosecant function, use `ArcCosecant` instead. Default None (equivalent to 1)
        """
        super().__init__("csc", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return 1 / np.sin(expr.value) ** (1 if power is None else power.value)


class Secant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "Secant":
        """The secant of an expression, optionally to some power, such as `\\sec^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the secant function.
        power : Optional[Token  |  Any], optional
            The power to which the secant is raised. Note that `power = -1` is *not* equivalent to `arcsec(a)`, but rather `1/sec(a)`. For the inverse secant function, use `ArcSecant` instead. Default None (equivalent to 1)
        """
        super().__init__("sec", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return 1 / np.cos(expr.value) ** (1 if power is None else power.value)


class Cotangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "Cotangent":
        """The cotangent of an expression, optionally to some power, such as `\\cot^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the cotangent function.
        power : Optional[Token  |  Any], optional
            The power to which the cotangent is raised. Note that `power = -1` is *not* equivalent to `arccot(a)`, but rather `1/cot(a)`. For the inverse cotangent function, use `ArcCotangent` instead. Default None (equivalent to 1)
        """
        super().__init__("cot", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return 1 / np.tan(expr.value) ** (1 if power is None else power.value)


class ArcCosecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "ArcCosecant":
        """The inverse cosecant of an expression, optionally to some power, such as `\\csc^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse cosecant function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse cosecant is raised. Default None (equivalent to 1)
        """
        super().__init__("csc", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.asin(1 / expr.value) ** (1 if power is None else power.value)


class ArcSecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "ArcSecant":
        """The inverse secant of an expression, optionally to some power, such as `\\sec^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse secant function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse secant is raised. Default None (equivalent to 1)
        """
        super().__init__("sec", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.acos(1 / expr.value) ** (1 if power is None else power.value)


class ArcCotangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "ArcCotangent":
        """The inverse cotangent of an expression, optionally to some power, such as `\\cot^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse cotangent function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse cotangent is raised. Default None (equivalent to 1)
        """
        super().__init__("cot", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.atan(1 / expr.value) ** (1 if power is None else power.value)


class HyperbolicSine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicSine":
        """The hyperbolic sine of an expression, optionally to some power, such as `\\sinh^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the hyperbolic sine function.
        power : Optional[Token  |  Any], optional
            The power to which the hyperbolic sine is raised. Default None (equivalent to 1)
        """
        super().__init__("sinh", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.sinh(expr.value) ** (1 if power is None else power.value)


class HyperbolicCosine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicCosine":
        """The hyperbolic cosine of an expression, optionally to some power, such as `\\cosh^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the hyperbolic cosine function.
        power : Optional[Token  |  Any], optional
            The power to which the hyperbolic cosine is raised. Default None (equivalent to 1)
        """
        super().__init__("cosh", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.cosh(expr.value) ** (1 if power is None else power.value)


class HyperbolicTangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicTangent":
        """The hyperbolic tangent of an expression, optionally to some power, such as `\\tanh^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the hyperbolic tangent function.
        power : Optional[Token  |  Any], optional
            The power to which the hyperbolic tangent is raised. Default None (equivalent to 1)
        """
        super().__init__("tanh", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.tanh(expr.value) ** (1 if power is None else power.value)


class HyperbolicCosecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicCosecant":
        """The hyperbolic cosecant of an expression, optionally to some power, such as `\\csch^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the hyperbolic cosecant function.
        power : Optional[Token  |  Any], optional
            The power to which the hyperbolic cosecant is raised. Default None (equivalent to 1)
        """
        super().__init__("csch", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return 1 / np.sinh(expr.value) ** (1 if power is None else power.value)


class HyperbolicSecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicSecant":
        """The hyperbolic secant of an expression, optionally to some power, such as `\\sech^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the hyperbolic secant function.
        power : Optional[Token  |  Any], optional
            The power to which the hyperbolic secant is raised. Default None (equivalent to 1)
        """
        super().__init__("sech", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return 1 / np.cosh(expr.value) ** (1 if power is None else power.value)


class HyperbolicCotangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicCotangent":
        """The hyperbolic cotangent of an expression, optionally to some power, such as `\\coth^2(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the hyperbolic cotangent function.
        power : Optional[Token  |  Any], optional
            The power to which the hyperbolic cotangent is raised. Default None (equivalent to 1)
        """
        super().__init__("coth", expr, power)

    def _operation(self, expr: Token, power: Token) -> Any:
        return 1 / np.tanh(expr.value) ** (1 if power is None else power.value)


class HyperbolicArcSine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicArcSine":
        """The inverse hyperbolic sine of an expression, optionally to some power, such as `\\sinh^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse hyperbolic sine function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse hyperbolic sine is raised. Default None (equivalent to 1)
        """
        super().__init__("sinh", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.asinh(expr.value) ** (1 if power is None else power.value)


class HyperbolicArcCosine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicArcCosine":
        """The inverse hyperbolic cosine of an expression, optionally to some power, such as `\\cosh^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse hyperbolic cosine function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse hyperbolic cosine is raised. Default None (equivalent to 1)
        """
        super().__init__("cosh", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.acosh(expr.value) ** (1 if power is None else power.value)


class HyperbolicArcTangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicArcTangent":
        """The inverse hyperbolic tangent of an expression, optionally to some power, such as `\\tanh^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse hyperbolic tangent function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse hyperbolic tangent is raised. Default None (equivalent to 1)
        """
        super().__init__("tanh", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.atanh(expr.value) ** (1 if power is None else power.value)


class HyperbolicArcCosecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicArcCosecant":
        """The inverse hyperbolic cosecant of an expression, optionally to some power, such as `\\csch^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse hyperbolic cosecant function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse hyperbolic cosecant is raised. Default None (equivalent to 1)
        """
        super().__init__("csch", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.asinh(1 / expr.value) ** (1 if power is None else power.value)


class HyperbolicArcSecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicArcSecant":
        """The inverse hyperbolic secant of an expression, optionally to some power, such as `\\sech^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse hyperbolic secant function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse hyperbolic secant is raised. Default None (equivalent to 1)
        """
        super().__init__("sech", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.acosh(1 / expr.value) ** (1 if power is None else power.value)


class HyperbolicArcCotangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> "HyperbolicArcCotangent":
        """The inverse hyperbolic cotangent of an expression, optionally to some power, such as `\\coth^{-1}(a)`. The value is calculated using the `math` library.

        Parameters
        ----------
        expr : Token | str
            The operand to the inverse hyperbolic cotangent function.
        power : Optional[Token  |  Any], optional
            The power to which the inverse hyperbolic cotangent is raised. Default None (equivalent to 1)
        """
        super().__init__("coth", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Token) -> Any:
        return np.atanh(1 / expr.value) ** (1 if power is None else power.value)


class Logarithm(CallableToken):
    def __init__(
        self, expr: Token | str | float, base: Token | str | float = 10
    ) -> "Logarithm":
        """A logarithm expression, such as `\\log_{10}(100)`.

        Parameters
        ----------
        value : Token | str | float
            The value to be logged.
        base : Token | str | float, optional
            The base of the logarithm. If this is 10, the base will be omitted. If it is the string `"e"`, the natural logarithm is used. Default 10
        """
        self.expr = as_token(expr)
        self.base = as_token(base)

    def __str__(self) -> str:
        if self.base.value == 10:
            return f"\\log\\left({{{self.expr}}}\\right)"
        elif self.base.value == "e":
            return f"\\ln\\left({{{self.expr}}}\\right)"
        return f"\\log_{{{self.base}}}\\left({{{self.expr}}}\\right)"

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        if self.base.value == "e":
            return Quantity(self.value)(*args, **kwargs)
        return Quantity(self.value)(*args, **kwargs)

    @property
    def value(self) -> float:
        if self.base.value == "e":
            return np.log(self.expr.value)
        if self.base.value == 10:
            return np.log10(self.expr.value)
        if self.base.value == 2:
            return np.log2(self.expr.value)
        return np.emath.logn(self.base.value, self.expr.value)


class NaturalLogarithm(Logarithm):
    def __init__(self, expr: Token | str | float) -> "NaturalLogarithm":
        super().__init__(expr, "e")

    def __str__(self) -> str:
        return f"\\ln\\left({{{self.expr}}}\\right)"


class Exponential(CallableToken):
    def __init__(
        self, expr: Token | str | float, use_exp: Optional[bool] = None
    ) -> "Exponential":
        """An exponential expression, such as `\\exp(a)`.

        Parameters
        ----------
        value : Token | str | float
            The value to be exponentiated.
        use_exp : Optional[bool], optional
            Whether to use the `exp` macro or `e` raised to the power of the value. If `None`, the default value (defined in `USE_EXP_FOR_EXPONENTIAL`) is used. Default None
        """
        self.expr = as_token(expr)
        self.use_exp = use_exp

    def __str__(self) -> str:
        use_exp = self.use_exp if self.use_exp is not None else USE_EXP_FOR_EXPONENTIAL
        if use_exp:
            return str(Collection(Macro("exp"), Bracket(self.expr, scale=True)))
        return str(Power(Macro("mathrm", "e"), self.expr))

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        return Quantity(self.value)(*args, **kwargs)

    @property
    def value(self) -> float:
        return np.exp(float(self.expr))


class Function(Token):
    def __init__(
        self,
        name: Token | str,
        *args: Token | str | Any,
        upright_name: bool = False,
        power: int | Token = None,
    ) -> "Function":
        """A function expression, such as `f(a, b)`.

        Parameters
        ----------
        name : Token | str
            The name of the function.
        *args : Token | str | Any
            The arguments to the function.
        """
        self.name = as_token(name)
        if upright_name:
            self.name = Macro("mathrm", self.name)
        self.args = [as_token(arg) for arg in args]
        self.power = None if power is None else as_token(power)

    def __str__(self) -> str:
        if len(self.args) == 0:
            if self.power is None:
                return str(self.name)
            return str(self.name**self.power)
        if len(self.args) == 1:
            if self.power is None:
                return str(self.name * (self.args[0],))
            return str(self.name**self.power * (self.args[0],))
        if self.power is None:
            return str(self.name * (Sequence(*self.args),))
        return str(self.name**self.power * (Sequence(*self.args),))


class FunctionGenerator(Token):
    def __init__(
        self, name: str | Token, upright_name: bool = False, power: int | Token = None
    ) -> "FunctionGenerator":
        """A function generator, which can be used to create functions with a given name. When called, these will accept a list of arguments and return a `Function` object.

        For example,
        ``` python
        f = FunctionGenerator("f")
        a = 2 * Variable("x")
        b = 3 * Variable("y")
        fab = f(a, b)
        print(fab) # "f(2x, 3y)"
        ```

        Parameters
        ----------
        name : str | Token
            The name of the function.
        upright_name : bool, optional
            Whether the name of the function should be upright (i.e. printed with `mathrm`). Default False
        """

        self.name = name
        self.upright_name = upright_name
        self.power = None if power is None else as_token(power)

    def __call__(self, *args: Token | str | Any, power: int | Token = None) -> Function:
        """Create a function with the given arguments.

        Parameters
        ----------
        *args : Token | str | Any
            The arguments to the function.

        Returns
        -------
        Function
            The function with the given arguments.
        """

        if power is None:
            power = self.power
        else:
            power = as_token(power)

        return Function(self.name, *args, upright_name=self.upright_name, power=power)

    def __str__(self):
        return self.name


class Operator(Function):
    def __init__(
        self, name: Token | str, *args: Token | str | Any, power: int | Token = None
    ) -> "Operator":
        """An operator expression, such as `cdf(a + b)`.

        Parameters
        ----------
        name : Token | str
            The name of the operator.
        *args : Token | str | Any
            The arguments to the operator.
        """
        super().__init__(name, *args, upright_name=True, power=power)


class OperatorGenerator(Token):
    def __init__(
        self, name: str | Token, power: int | Token = None
    ) -> "OperatorGenerator":
        """An operator generator, which can be used to create operators with a given name. When called, these will accept a list of arguments and return an `Operator` object.

        For example,
        ``` python
        cdf = OperatorGenerator("cdf")
        a = 2 * Variable("x")
        b = 3 * Variable("y")
        cdfab = cdf(a + b)
        print(cdfab) # "\\mathrm{cdf}(2x + 3y)"
        ```

        Parameters
        ----------
        name : str | Token
            The name of the operator.
        """

        self.name = name
        self.power = power

    def __call__(self, *args: Token | str | Any, power: int | Token = None) -> Operator:
        """Create an operator with the given arguments.

        Parameters
        ----------
        *args : Token | str | Any
            The arguments to the operator.

        Returns
        -------
        Operator
            The operator with the given arguments.
        """

        if power is None:
            power = self.power
        else:
            power = as_token(power)

        return Operator(self.name, *args, power=power)

    def __str__(self):
        if self.power is None or self.power == 1:
            return str(Macro("mathrm", self.name))
        else:
            return str(Macro("mathrm", self.name) ** self.power)


# =============================================================================


# Greek Letters


alpha = Macro("alpha")
beta = Macro("beta")
gamma = Macro("gamma")
delta = Macro("delta")
epsilon = Macro("epsilon")
varepsilon = Macro("varepsilon")
zeta = Macro("zeta")
eta = Macro("eta")
theta = Macro("theta")
vartheta = Macro("vartheta")
iota = Macro("iota")
kappa = Macro("kappa")
lambda_ = Macro("lambda")
mu = Macro("mu")
nu = Macro("nu")
xi = Macro("xi")
pi = Variable("\\pi", 3.1415926535897932384626433832795028841971693993751058209749445)
varpi = Macro("varpi")
rho = Macro("rho")
varrho = Macro("varrho")
sigma = Macro("sigma")
varsigma = Macro("varsigma")
tau = Macro("tau")
upsilon = Macro("upsilon")
phi = Macro("phi")
varphi = Macro("varphi")
chi = Macro("chi")
psi = Macro("psi")
omega = Macro("omega")
Gamma = Macro("Gamma")
Delta = Macro("Delta")
Theta = Macro("Theta")
Lambda = Macro("Lambda")
Xi = Macro("Xi")
Pi = Macro("Pi")
Sigma = Macro("Sigma")
Upsilon = Macro("Upsilon")
Phi = Macro("Phi")
Psi = Macro("Psi")
Omega = Macro("Omega")

nabla = Macro("nabla")

i = Literal("i")

# == Functions ================================================================


def power(base: Token | str | float, exponent: Token | str | float) -> Power:
    """Raise a base to an exponent, such as `a^b`.

    Parameters
    ----------
    base : Token | str | float
        The base of the power.
    exponent : Token | str | float
        The exponent of the power.

    Returns
    -------
    Power
        The base raised to the exponent.
    """
    return Power(base, exponent)


def index(base: Token | str | float, index: Token | str | float) -> Index:
    """Add an index to a base, such as `a_b`.

    Parameters
    ----------
    base : Token | str | float
        The base of the index.
    index : Token | str | float
        The index of the base.

    Returns
    -------
    Index
        The base with the index.
    """
    return Index(base, index)


def math_sup(exponent: Token | str | float) -> Power:
    """Raise the following expression to an exponent, such as `{}^b`.

    Parameters
    ----------
    exponent : Token | str | float
        The exponent of the power.

    Returns
    -------
    Power
        The base raised to the exponent.
    """
    return Power("", exponent)


def math_sub(index: Token | str | float) -> Index:
    """Add an index to the following expression, such as `{}_b`.

    Parameters
    ----------
    index : Token | str | float
        The index of the base.

    Returns
    -------
    Index
        The base with the index.
    """
    return Index("", index)


def frac(numerator: Token | str | float, denominator: Token | str | float) -> Division:
    """Create a fraction, such as `\\frac{a}{b}`.

    Parameters
    ----------
    numerator : Token | str | float
        The numerator of the fraction.
    denominator : Token | str | float
        The denominator of the fraction.

    Returns
    -------
    Division
        The fraction.
    """
    return Division(numerator, denominator)


def dfrac(numerator: Token | str | float, denominator: Token | str | float) -> Division:
    """Create a fraction with display mode, such as `\\dfrac{a}{b}`.

    Parameters
    ----------
    numerator : Token | str | float
        The numerator of the fraction.
    denominator : Token | str | float
        The denominator of the fraction.

    Returns
    -------
    Division
        The fraction.
    """
    return Division(numerator, denominator, display_mode=True)


def dot(expr: Token | str | float) -> Macro:
    """Add a dot above the following expression, such as `\\dot{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the dot is added.

    Returns
    -------
    Macro
        The expression with a dot above it.
    """
    return Macro("dot", expr)


def ddot(expr: Token | str | float) -> Macro:
    """Add a double dot above the following expression, such as `\\ddot{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the double dot is added.

    Returns
    -------
    Macro
        The expression with a double dot above it.
    """
    return Macro("ddot", expr)


def hat(expr: Token | str | float) -> Macro:
    """Add a hat above the following expression, such as `\\hat{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the hat is added.

    Returns
    -------
    Macro
        The expression with a hat above it.
    """
    return Macro("hat", expr)


def bar(expr: Token | str | float) -> Macro:
    """Add a bar above the following expression, such as `\\bar{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the bar is added.

    Returns
    -------
    Macro
        The expression with a bar above it.
    """
    return Macro("bar", expr)


def vec(expr: Token | str | float) -> Macro:
    """Add a vector arrow above the following expression, such as `\\vec{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the vector arrow is added.

    Returns
    -------
    Macro
        The expression with a vector arrow above it.
    """
    return Macro("vec", expr)


def underline(expr: Token | str | float) -> Macro:
    """Add an underline below the following expression, such as `\\underline{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the underline is added.

    Returns
    -------
    Macro
        The underlined expression.
    """
    return Macro("underline", expr)


def tilde(expr: Token | str | float) -> Macro:
    """Add a tilde above the following expression, such as `\\tilde{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the tilde is added.

    Returns
    -------
    Macro
        The expression with a tilde above it.
    """
    return Macro("tilde", expr)


def widehat(expr: Token | str | float) -> Macro:
    """Add a wide hat above the following expression, such as `\\widehat{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the wide hat is added.

    Returns
    -------
    Macro
        The expression with a wide hat above it.
    """
    return Macro("widehat", expr)


def widebar(expr: Token | str | float) -> Macro:
    """Add a wide bar above the following expression, such as `\\widebar{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the wide bar is added.

    Returns
    -------
    Macro
        The expression with a wide bar above it.
    """
    return Macro("widebar", expr)


overline = widebar


def widetilde(expr: Token | str | float) -> Macro:
    """Add a wide tilde above the following expression, such as `\\widetilde{a}`.

    Parameters
    ----------
    expr : Token | str | float
        The expression to which the wide tilde is added.

    Returns
    -------
    Macro
        The expression with a wide tilde above it.
    """
    return Macro("widetilde", expr)


def sin(expr: Token | str | float, power: Optional[Token | str | float] = None) -> Sine:
    """The sine of an expression, optionally to some power, such as `\\sin^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the sine function.
    power : Optional[Token  |  Any], optional
        The power to which the sine is raised. Note that `power = -1` is *not* equivalent to `arcsin(a)`, but rather `1/sin(a)`. For the inverse sine function, use `ArcSine` instead. Default None (equivalent to 1)

    Returns
    -------
    Sine
        The sine of the expression.
    """
    return Sine(expr, power)


def cos(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> Cosine:
    """The cosine of an expression, optionally to some power, such as `\\cos^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the cosine function.
    power : Optional[Token  |  Any], optional
        The power to which the cosine is raised. Note that `power = -1` is *not* equivalent to `arccos(a)`, but rather `1/cos(a)`. For the inverse cosine function, use `ArcCosine` instead. Default None (equivalent to 1)

    Returns
    -------
    Cosine
        The cosine of the expression.
    """
    return Cosine(expr, power)


def tan(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> Tangent:
    """The tangent of an expression, optionally to some power, such as `\\tan^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the tangent function.
    power : Optional[Token  |  Any], optional
        The power to which the tangent is raised. Note that `power = -1` is *not* equivalent to `arctan(a)`, but rather `1/tan(a)`. For the inverse tangent function, use `ArcTangent` instead. Default None (equivalent to 1)

    Returns
    -------
    Tangent
        The tangent of the expression.
    """
    return Tangent(expr, power)


def arcsin(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> ArcSine:
    """The inverse sine of an expression, optionally to some power, such as `\\sin^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse sine function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse sine is raised. Default None (equivalent to 1)

    Returns
    -------
    ArcSine
        The inverse sine of the expression.
    """
    return ArcSine(expr, power)


def arccos(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> ArcCosine:
    """The inverse cosine of an expression, optionally to some power, such as `\\cos^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse cosine function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse cosine is raised. Default None (equivalent to 1)

    Returns
    -------
    ArcCosine
        The inverse cosine of the expression.
    """
    return ArcCosine(expr, power)


def arctan(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> ArcTangent:
    """The inverse tangent of an expression, optionally to some power, such as `\\tan^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse tangent function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse tangent is raised. Default None (equivalent to 1)

    Returns
    -------
    ArcTangent
        The inverse tangent of the expression.
    """
    return ArcTangent(expr, power)


asin = arcsin
acos = arccos
atan = arctan


def csc(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> Cosecant:
    """The cosecant of an expression, optionally to some power, such as `\\csc^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the cosecant function.
    power : Optional[Token  |  Any], optional
        The power to which the cosecant is raised. Note that `power = -1` is *not* equivalent to `arccsc(a)`, but rather `1/csc(a)`. For the inverse cosecant function, use `ArcCosecant` instead. Default None (equivalent to 1)

    Returns
    -------
    Cosecant
        The cosecant of the expression.
    """
    return Cosecant(expr, power)


def sec(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> Secant:
    """The secant of an expression, optionally to some power, such as `\\sec^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the secant function.
    power : Optional[Token  |  Any], optional
        The power to which the secant is raised. Note that `power = -1` is *not* equivalent to `arcsec(a)`, but rather `1/sec(a)`. For the inverse secant function, use `ArcSecant` instead. Default None (equivalent to 1)

    Returns
    -------
    Secant
        The secant of the expression.
    """
    return Secant(expr, power)


def cot(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> Cotangent:
    """The cotangent of an expression, optionally to some power, such as `\\cot^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the cotangent function.
    power : Optional[Token  |  Any], optional
        The power to which the cotangent is raised. Note that `power = -1` is *not* equivalent to `arccot(a)`, but rather `1/cot(a)`. For the inverse cotangent function, use `ArcCotangent` instead. Default None (equivalent to 1)

    Returns
    -------
    Cotangent
        The cotangent of the expression.
    """
    return Cotangent(expr, power)


def arccsc(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> ArcCosecant:
    """The inverse cosecant of an expression, optionally to some power, such as `\\csc^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse cosecant function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse cosecant is raised. Default None (equivalent to 1)

    Returns
    -------
    ArcCosecant
        The inverse cosecant of the expression.
    """
    return ArcCosecant(expr, power)


def arcsec(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> ArcSecant:
    """The inverse secant of an expression, optionally to some power, such as `\\sec^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse secant function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse secant is raised. Default None (equivalent to 1)

    Returns
    -------
    ArcSecant
        The inverse secant of the expression.
    """
    return ArcSecant(expr, power)


def arccot(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> ArcCotangent:
    """The inverse cotangent of an expression, optionally to some power, such as `\\cot^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse cotangent function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse cotangent is raised. Default None (equivalent to 1)

    Returns
    -------
    ArcCotangent
        The inverse cotangent of the expression.
    """
    return ArcCotangent(expr, power)


acsc = arccsc
asec = arcsec
acot = arccot


def sinh(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicSine:
    """The hyperbolic sine of an expression, optionally to some power, such as `\\sinh^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the hyperbolic sine function.
    power : Optional[Token  |  Any], optional
        The power to which the hyperbolic sine is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicSine
        The hyperbolic sine of the expression.
    """
    return HyperbolicSine(expr, power)


def cosh(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicCosine:
    """The hyperbolic cosine of an expression, optionally to some power, such as `\\cosh^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the hyperbolic cosine function.
    power : Optional[Token  |  Any], optional
        The power to which the hyperbolic cosine is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicCosine
        The hyperbolic cosine of the expression.
    """
    return HyperbolicCosine(expr, power)


def tanh(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicTangent:
    """The hyperbolic tangent of an expression, optionally to some power, such as `\\tanh^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the hyperbolic tangent function.
    power : Optional[Token  |  Any], optional
        The power to which the hyperbolic tangent is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicTangent
        The hyperbolic tangent of the expression.
    """
    return HyperbolicTangent(expr, power)


def csch(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicCosecant:
    """The hyperbolic cosecant of an expression, optionally to some power, such as `\\csch^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the hyperbolic cosecant function.
    power : Optional[Token  |  Any], optional
        The power to which the hyperbolic cosecant is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicCosecant
        The hyperbolic cosecant of the expression.
    """
    return HyperbolicCosecant(expr, power)


def sech(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicSecant:
    """The hyperbolic secant of an expression, optionally to some power, such as `\\sech^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the hyperbolic secant function.
    power : Optional[Token  |  Any], optional
        The power to which the hyperbolic secant is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicSecant
        The hyperbolic secant of the expression.
    """
    return HyperbolicSecant(expr, power)


def coth(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicCotangent:
    """The hyperbolic cotangent of an expression, optionally to some power, such as `\\coth^2(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the hyperbolic cotangent function.
    power : Optional[Token  |  Any], optional
        The power to which the hyperbolic cotangent is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicCotangent
        The hyperbolic cotangent of the expression.
    """
    return HyperbolicCotangent(expr, power)


def arcsinh(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicArcSine:
    """The inverse hyperbolic sine of an expression, optionally to some power, such as `\\sinh^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse hyperbolic sine function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse hyperbolic sine is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicArcSine
        The inverse hyperbolic sine of the expression.
    """
    return HyperbolicArcSine(expr, power)


def arccosh(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicArcCosine:
    """The inverse hyperbolic cosine of an expression, optionally to some power, such as `\\cosh^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse hyperbolic cosine function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse hyperbolic cosine is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicArcCosine
        The inverse hyperbolic cosine of the expression.
    """
    return HyperbolicArcCosine(expr, power)


def arctanh(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicArcTangent:
    """The inverse hyperbolic tangent of an expression, optionally to some power, such as `\\tanh^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse hyperbolic tangent function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse hyperbolic tangent is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicArcTangent
        The inverse hyperbolic tangent of the expression.
    """
    return HyperbolicArcTangent(expr, power)


def arccsch(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicArcCosecant:
    """The inverse hyperbolic cosecant of an expression, optionally to some power, such as `\\csch^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse hyperbolic cosecant function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse hyperbolic cosecant is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicArcCosecant
        The inverse hyperbolic cosecant of the expression.
    """
    return HyperbolicArcCosecant(expr, power)


def arcsech(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicArcSecant:
    """The inverse hyperbolic secant of an expression, optionally to some power, such as `\\sech^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse hyperbolic secant function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse hyperbolic secant is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicArcSecant
        The inverse hyperbolic secant of the expression.
    """
    return HyperbolicArcSecant(expr, power)


def arccoth(
    expr: Token | str | float, power: Optional[Token | str | float] = None
) -> HyperbolicArcCotangent:
    """The inverse hyperbolic cotangent of an expression, optionally to some power, such as `\\coth^{-1}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    expr : Token | str
        The operand to the inverse hyperbolic cotangent function.
    power : Optional[Token  |  Any], optional
        The power to which the inverse hyperbolic cotangent is raised. Default None (equivalent to 1)

    Returns
    -------
    HyperbolicArcCotangent
        The inverse hyperbolic cotangent of the expression.
    """
    return HyperbolicArcCotangent(expr, power)


asinh = arcsinh
acosh = arccosh
atanh = arctanh
acsch = arccsch
asech = arcsech
acoth = arccoth


def log(value: Token | str | float, base: Token | str | float = 10) -> Logarithm:
    """The logarithm of an expression, optionally to some base, such as `\\log_{10}(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    value : Token | str
        The operand to the logarithm function.
    base : Token | str, optional
        The base of the logarithm. If this is the string `"e"`, the natural logarithm will be used instead. Default 10

    Returns
    -------
    Logarithm
        The logarithm of the expression.
    """
    return Logarithm(value, base)


def ln(value: Token | str | float) -> NaturalLogarithm:
    """The natural logarithm of an expression, such as `\\ln(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    value : Token | str
        The operand to the natural logarithm function.

    Returns
    -------
    NaturalLogarithm
        The natural logarithm of the expression.
    """
    return NaturalLogarithm(value)


def exp(value: Token | str | float, use_exp: Optional[bool] = None) -> Exponential:
    """The exponential of an expression, such as `\\exp(a)`. The value is calculated using the `math` library.

    Parameters
    ----------
    value : Token | str
        The value to be exponentiated.
    use_exp : Optional[bool], optional
        Whether to use the `exp` macro or `e` raised to the power of the value. If `None`, the default value (defined in `USE_EXP_FOR_EXPONENTIAL`) is used. Default None
    """
    return Exponential(value, use_exp)


def bracket(*children: Token | str | float) -> Bracket:
    """A set of brackets, such as `(a, b, c)`.

    Parameters
    ----------
    *children : Token | str | float
        The children of the bracket.

    Returns
    -------
    Bracket
        The bracket containing the children.
    """
    return Bracket(*children)


paren = bracket


def square_bracket(*children: Token | str | float) -> SquareBracket:
    """A set of square brackets, such as `[a, b, c]`.

    Parameters
    ----------
    *children : Token | str | float
        The children of the square bracket.

    Returns
    -------
    SquareBracket
        The square bracket containing the children.
    """
    return SquareBracket(*children)


def curly_bracket(*children: Token | str | float) -> CurlyBracket:
    """A set of curly brackets, such as `{a, b, c}`.

    Parameters
    ----------
    *children : Token | str | float
        The children of the curly bracket.

    Returns
    -------
    CurlyBracket
        The curly bracket containing the children.
    """
    return CurlyBracket(*children)


brace = curly_bracket


def absolute(*children: Token | str | float) -> AbsoluteValue:
    """The absolute value of an expression, such as `|a|`.

    Parameters
    ----------
    *children : Token | str | float
        The children of the absolute value.

    Returns
    -------
    AbsoluteValue
        The absolute value containing the children.
    """
    return AbsoluteValue(*children)


def angle_bracket(*children: Token | str | float) -> AngleBracket:
    """A set of angle brackets, such as `<a, b, c>`.

    Parameters
    ----------
    *children : Token | str | float
        The children of the angle bracket.

    Returns
    -------
    AngleBracket
        The angle bracket containing the children.
    """
    return AngleBracket(*children)


sym = as_token


def var(
    name: str,
    value: float,
    fmt: Optional[str] = None,
    unit: Optional[pint.Unit | str] = None,
) -> Variable:
    """A variable with a name, value, and optional unit and format specifier.

    Parameters
    ----------
    name : str
        The name of the variable. This will be used when rendering the variable directly.
    value : float
        The value of the variable. This will be used when the variable is called as a function.
    fmt : Optional[str], optional
        The format specifier to use when rendering the variable. If None, the default format specifier will be used. If `fmt = ''`, no format specifier will be used. Default None
    unit : Optional[pint.Unit  |  str], optional
        The unit of the variable. This can be a pint.Unit object, a string in siunitx format (e.g. `\meter\per\second\squared`), written fully (meter per second squared), or abbreviated (m/s^2 or m s^-2). If None, the value will be assumed to be dimensionless. Default None
    """
    return Variable(name, value, fmt, unit)


comma = Literal("\\,,")
period = Literal("\\,.")
newline = Literal("\\\\")
empty = Literal("")
alignment = Literal("&")
space = Literal("\\ ")
smallspace = Literal("\\,")

zero, one, two, three, four, five, six, seven, eight, nine = map(Literal, range(10))
inf = Macro("infty")
infinity = inf
infty = inf


def sanitise_latex_text(text: str) -> str:
    # escape special characters, if they are not already escaped
    replacements = [
        ("$", "\\$"),
        ("&", "\\&"),
        ("#", "\\#"),
        ("%", "\\%"),
        ("_", "\\_"),
        ("^", "\\^"),
        ("~", "\\textasciitilde "),
        ("|", "\\textbar "),
        ("<", "\\textless "),
        (">", "\\textgreater "),
    ]
    for old, new in replacements:
        text = re.sub(rf"(?<!\\){re.escape(old)}", new, text)
    return text


def text(text: str) -> Macro:
    text = sanitise_latex_text(text)
    return Macro("text", text)


def texttt(text: str) -> Macro:
    text = sanitise_latex_text(text)
    return Macro("texttt", text)


def textbf(text: str) -> Macro:
    text = sanitise_latex_text(text)
    return Macro("textbf", text)


def textit(text: str) -> Macro:
    text = sanitise_latex_text(text)
    return Macro("textit", text)


def textsc(text: str) -> Macro:
    text = sanitise_latex_text(text)
    return Macro("textsc", text)


# == Symbols parsing ==========================================================


def __pythonify_name(name: str) -> str:
    # convert a string into a valid python variable name
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


def define_symbols(
    statements: str,
    namespace: Optional[Dict[str, Any]] = None,
    # write_to_namespace: bool = False
) -> None | Tuple[Token]:
    # Each line consists of `var = value units (fmt);`, `value`, `units`, `fmt` optional.
    # If all three are omitted, the line can be `var;`
    # They don't have to be separated by newlines.
    statement_list = statements.split("\n")
    statement_list = [stmt.split(";") for stmt in statement_list]
    # collapse the list to 1d
    statement_list = [stmt.strip() for stmts in statement_list for stmt in stmts]
    # remove comments which start with #
    statement_list = [stmt.split("#")[0].strip() for stmt in statement_list]

    # remove empty lines
    statement_list = [stmt for stmt in statement_list if stmt]
    assignments = []
    for statement in statement_list:
        if not "=" in statement:
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
        # TODO: Handle string values. We *shouldn't* get a string with units or a fmt specifier, but we could.
        # For now, raise an exception
        if "'" in value or '"' in value:
            raise NotImplementedError("String values are not yet supported")
        # parse the value
        matched = __value_pattern.match(value)
        if matched is None:
            raise ValueError(f"Could not parse value `{value}`")
        value = matched.group("value")
        units = matched.group("units")
        fmt = matched.group("fmt")
        new_name = __pythonify_name(name)
        if namespace is not None and new_name in namespace:
            raise ValueError(f"Symbol {new_name} already defined")
        value = float(value)
        if value.is_integer():
            value = int(value)
        new_symbol = var(name, value, unit=units, fmt=fmt)
        if namespace is not None:
            namespace[new_name] = new_symbol
        assignments.append(new_symbol)
    return tuple(assignments)


symbols = define_symbols


def split(
    lines: List[str | Token | Tuple[str | Token]],
    environment="split",
    separator: str | None = "=",
) -> str:
    if not isinstance(lines, (list, tuple)):
        lines = [lines]
    for i, line in enumerate(lines):
        if isinstance(line, (list, tuple)):
            if len(line) == 1:
                lines[i] = f"& {separator if separator is not None else '='} {line[0]}"
            else:
                if separator is None:
                    lines[i] = " & ".join(str(expr) for expr in line)
                if len(line) == 2:
                    lines[i] = f"{line[0]} & {separator} {line[1]}"
                else:
                    lines[i] = f"{line[0]} & {separator} {line[1]} & " + " & ".join(
                        str(expr) for expr in line[2:]
                    )
        else:
            lines[i] = str(line)
    return (
        f"\\begin{{{environment}}}\n\t"
        + "\\\\\n\t".join(lines)
        + f"\n\\end{{{environment}}}"
    )
