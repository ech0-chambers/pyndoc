"""Mathematical functions, trigonometric operations, exponentials, and logarithms."""

from abc import ABC, abstractmethod
from typing import Optional, Any
import numpy as np
import pint
from .config import ACTIVE_CONFIG
from .core import (
    Token,
    CallableToken,
    Literal,
    Macro,
    Division,
    Power,
    Index,
    as_token,
)
from .containers import Bracket, Collection, Sequence


class NthRoot(CallableToken):
    def __init__(
        self, expr: Token | str | float, root: Token | str | float = 2
    ) -> None:
        """The nth root of a value, such as `\\sqrt{a}` or `\\sqrt[3]{a}`."""
        self.expr = as_token(expr)
        self.root = as_token(root)

    def __str__(self) -> str:
        if self.root.value == 2:
            return f"\\sqrt{{{self.expr}}}"
        return f"\\sqrt[{self.root}]{{{self.expr}}}"

    @property
    def value(self) -> Any:
        return self.expr.value ** (1 / self.root.value)

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        return as_token(self.value)(*args, **kwargs)


def sqrt(value: Token | str | float) -> NthRoot:
    """The square root of a value, such as `\\sqrt{a}`."""
    return NthRoot(value, 2)


def cbrt(value: Token | str | float) -> NthRoot:
    """The cube root of a value, such as `\\sqrt[3]{a}`."""
    return NthRoot(value, 3)


class _TrigFunction(CallableToken, ABC):
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

    @property
    def value(self) -> Any:
        return self._operation(self.expr, self.power)

    def _eval_angle_arg(self, expr: Token) -> Any:
        raw_val = expr.value
        if isinstance(raw_val, pint.Quantity):
            unit_dict = dict(raw_val.units._units)
            angle_units = {"degree", "arcdeg", "arcminute", "arcsecond"}
            if any(u in angle_units for u in unit_dict):
                target_parts = []
                for u_name, p in unit_dict.items():
                    if u_name in angle_units:
                        target_parts.append(f"radian**{p}")
                    else:
                        target_parts.append(f"{u_name}**{p}")
                target_unit = " * ".join(target_parts)
                return raw_val.to(target_unit).magnitude
            elif "radian" in unit_dict:
                return raw_val.magnitude
            else:
                mag = raw_val.magnitude
                return np.deg2rad(mag) if ACTIVE_CONFIG.use_degrees else mag
        if ACTIVE_CONFIG.use_degrees:
            return np.deg2rad(raw_val)
        return raw_val

    def _eval_inverse_result(self, rad_val: Any) -> Any:
        if ACTIVE_CONFIG.use_degrees:
            return np.rad2deg(rad_val)
        return rad_val

    def __str__(self) -> str:
        if self.inverse:
            if ACTIVE_CONFIG.use_arc_for_inverse_trig:
                fn_name = f"arc{self.name}"
                if self.power is None:
                    return str(Collection(Macro(fn_name), Bracket(self.expr, scale=True)))
                return str(
                    Collection(
                        Power(Macro(fn_name), self.power), Bracket(self.expr, scale=True)
                    )
                )
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
        return as_token(self.value)(*args, **kwargs)

    @abstractmethod
    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        pass


class Sine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("sin", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = np.sin(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class Cosine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("cos", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = np.cos(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class Tangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("tan", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = np.tan(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class ArcSine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("sin", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = self._eval_inverse_result(np.asin(expr.value))
        return val ** (1 if power is None else power.value)


class ArcCosine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("cos", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = self._eval_inverse_result(np.acos(expr.value))
        return val ** (1 if power is None else power.value)


class ArcTangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("tan", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = self._eval_inverse_result(np.atan(expr.value))
        return val ** (1 if power is None else power.value)


class Cosecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("csc", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = 1 / np.sin(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class Secant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("sec", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = 1 / np.cos(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class Cotangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("cot", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = 1 / np.tan(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class ArcCosecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("csc", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = self._eval_inverse_result(np.asin(1 / expr.value))
        return val ** (1 if power is None else power.value)


class ArcSecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("sec", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = self._eval_inverse_result(np.acos(1 / expr.value))
        return val ** (1 if power is None else power.value)


class ArcCotangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("cot", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = self._eval_inverse_result(np.atan(1 / expr.value))
        return val ** (1 if power is None else power.value)


class HyperbolicSine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("sinh", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = np.sinh(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class HyperbolicCosine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("cosh", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = np.cosh(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class HyperbolicTangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("tanh", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = np.tanh(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class HyperbolicCosecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("csch", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = 1 / np.sinh(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class HyperbolicSecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("sech", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = 1 / np.cosh(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class HyperbolicCotangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("coth", expr, power)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        val = 1 / np.tanh(self._eval_angle_arg(expr))
        return val ** (1 if power is None else power.value)


class HyperbolicArcSine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("sinh", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        return np.asinh(expr.value) ** (1 if power is None else power.value)


class HyperbolicArcCosine(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("cosh", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        return np.acosh(expr.value) ** (1 if power is None else power.value)


class HyperbolicArcTangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("tanh", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        return np.atanh(expr.value) ** (1 if power is None else power.value)


class HyperbolicArcCosecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("csch", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        return np.asinh(1 / expr.value) ** (1 if power is None else power.value)


class HyperbolicArcSecant(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("sech", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        return np.acosh(1 / expr.value) ** (1 if power is None else power.value)


class HyperbolicArcCotangent(_TrigFunction):
    def __init__(
        self, expr: Token | str, power: Optional[Token | Any] = None
    ) -> None:
        super().__init__("coth", expr, power, inverse=True)

    def _operation(self, expr: Token, power: Optional[Token]) -> Any:
        return np.atanh(1 / expr.value) ** (1 if power is None else power.value)


class Logarithm(CallableToken):
    def __init__(
        self, expr: Token | str | float, base: Token | str | float = 10
    ) -> None:
        """A logarithm expression, such as `\\log_{10}(100)`."""
        self.expr = as_token(expr)
        self.base = as_token(base)

    def __str__(self) -> str:
        if self.base.value == 10:
            return f"\\log\\left({{{self.expr}}}\\right)"
        elif self.base.value == "e":
            return f"\\ln\\left({{{self.expr}}}\\right)"
        return f"\\log_{{{self.base}}}\\left({{{self.expr}}}\\right)"

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        return as_token(self.value)(*args, **kwargs)

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
    def __init__(self, expr: Token | str | float) -> None:
        super().__init__(expr, "e")

    def __str__(self) -> str:
        return f"\\ln\\left({{{self.expr}}}\\right)"


class Exponential(CallableToken):
    def __init__(
        self, expr: Token | str | float, use_exp: Optional[bool] = None
    ) -> None:
        """An exponential expression, such as `\\exp(a)`."""
        self.expr = as_token(expr)
        self.use_exp = use_exp

    def __str__(self) -> str:
        use_exp = (
            self.use_exp
            if self.use_exp is not None
            else ACTIVE_CONFIG.use_exp_for_exponential
        )
        if use_exp:
            return str(Collection(Macro("exp"), Bracket(self.expr, scale=True)))
        return str(Power(Macro("mathrm", "e"), self.expr))

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        return as_token(self.value)(*args, **kwargs)

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
    ) -> None:
        """A function expression, such as `f(a, b)`."""
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
    ) -> None:
        self.name = name
        self.upright_name = upright_name
        self.power = None if power is None else as_token(power)

    def __call__(self, *args: Token | str | Any, power: int | Token = None) -> Function:
        if power is None:
            power = self.power
        else:
            power = as_token(power)
        return Function(self.name, *args, upright_name=self.upright_name, power=power)

    def __str__(self) -> str:
        return str(self.name)


class Operator(Function):
    def __init__(
        self, name: Token | str, *args: Token | str | Any, power: int | Token = None
    ) -> None:
        super().__init__(name, *args, upright_name=True, power=power)


class OperatorGenerator(Token):
    def __init__(
        self, name: str | Token, power: int | Token = None
    ) -> None:
        self.name = name
        self.power = power

    def __call__(self, *args: Token | str | Any, power: int | Token = None) -> Operator:
        if power is None:
            power = self.power
        else:
            power = as_token(power)
        return Operator(self.name, *args, power=power)

    def __str__(self) -> str:
        if self.power is None or self.power == 1:
            return str(Macro("mathrm", self.name))
        return str(Macro("mathrm", self.name) ** self.power)


# Standalone function helpers
def sin(expr: Token | str | float, power: Optional[Token | str | float] = None) -> Sine:
    return Sine(expr, power)


def cos(expr: Token | str | float, power: Optional[Token | str | float] = None) -> Cosine:
    return Cosine(expr, power)


def tan(expr: Token | str | float, power: Optional[Token | str | float] = None) -> Tangent:
    return Tangent(expr, power)


def arcsin(expr: Token | str | float, power: Optional[Token | str | float] = None) -> ArcSine:
    return ArcSine(expr, power)


def arccos(expr: Token | str | float, power: Optional[Token | str | float] = None) -> ArcCosine:
    return ArcCosine(expr, power)


def arctan(expr: Token | str | float, power: Optional[Token | str | float] = None) -> ArcTangent:
    return ArcTangent(expr, power)


asin = arcsin
acos = arccos
atan = arctan


def csc(expr: Token | str | float, power: Optional[Token | str | float] = None) -> Cosecant:
    return Cosecant(expr, power)


def sec(expr: Token | str | float, power: Optional[Token | str | float] = None) -> Secant:
    return Secant(expr, power)


def cot(expr: Token | str | float, power: Optional[Token | str | float] = None) -> Cotangent:
    return Cotangent(expr, power)


def arccsc(expr: Token | str | float, power: Optional[Token | str | float] = None) -> ArcCosecant:
    return ArcCosecant(expr, power)


def arcsec(expr: Token | str | float, power: Optional[Token | str | float] = None) -> ArcSecant:
    return ArcSecant(expr, power)


def arccot(expr: Token | str | float, power: Optional[Token | str | float] = None) -> ArcCotangent:
    return ArcCotangent(expr, power)


acsc = arccsc
asec = arcsec
acot = arccot


def sinh(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicSine:
    return HyperbolicSine(expr, power)


def cosh(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicCosine:
    return HyperbolicCosine(expr, power)


def tanh(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicTangent:
    return HyperbolicTangent(expr, power)


def csch(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicCosecant:
    return HyperbolicCosecant(expr, power)


def sech(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicSecant:
    return HyperbolicSecant(expr, power)


def coth(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicCotangent:
    return HyperbolicCotangent(expr, power)


def arcsinh(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicArcSine:
    return HyperbolicArcSine(expr, power)


def arccosh(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicArcCosine:
    return HyperbolicArcCosine(expr, power)


def arctanh(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicArcTangent:
    return HyperbolicArcTangent(expr, power)


def arccsch(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicArcCosecant:
    return HyperbolicArcCosecant(expr, power)


def arcsech(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicArcSecant:
    return HyperbolicArcSecant(expr, power)


def arccoth(expr: Token | str | float, power: Optional[Token | str | float] = None) -> HyperbolicArcCotangent:
    return HyperbolicArcCotangent(expr, power)


asinh = arcsinh
acosh = arccosh
atanh = arctanh
acsch = arccsch
asech = arcsech
acoth = arccoth


def log(value: Token | str | float, base: Token | str | float = 10) -> Logarithm:
    return Logarithm(value, base)


def ln(value: Token | str | float) -> NaturalLogarithm:
    return NaturalLogarithm(value)


def exp(value: Token | str | float, use_exp: Optional[bool] = None) -> Exponential:
    return Exponential(value, use_exp)


def power(base: Token | str | float, exponent: Token | str | float) -> Power:
    """Raise a base to an exponent, such as `a^b`."""
    return Power(base, exponent)


def index(base: Token | str | float, index: Token | str | float) -> Index:
    """Add an index to a base, such as `a_b`."""
    return Index(base, index)


def math_sup(exponent: Token | str | float) -> Power:
    """Raise the following expression to an exponent, such as `{}^b`."""
    return Power("", exponent)


def math_sub(index: Token | str | float) -> Index:
    """Add an index to the following expression, such as `{}_b`."""
    return Index("", index)


def frac(numerator: Token | str | float, denominator: Token | str | float) -> Division:
    """Create a fraction, such as `\\frac{a}{b}`."""
    return Division(numerator, denominator)


def dfrac(numerator: Token | str | float, denominator: Token | str | float) -> Division:
    """Create a fraction with display mode, such as `\\dfrac{a}{b}`."""
    return Division(numerator, denominator, display_mode=True)


__all__ = [
    "NthRoot",
    "sqrt",
    "cbrt",
    "power",
    "index",
    "math_sup",
    "math_sub",
    "frac",
    "dfrac",
    "_TrigFunction",
    "Sine",
    "Cosine",
    "Tangent",
    "ArcSine",
    "ArcCosine",
    "ArcTangent",
    "Cosecant",
    "Secant",
    "Cotangent",
    "ArcCosecant",
    "ArcSecant",
    "ArcCotangent",
    "HyperbolicSine",
    "HyperbolicCosine",
    "HyperbolicTangent",
    "HyperbolicCosecant",
    "HyperbolicSecant",
    "HyperbolicCotangent",
    "HyperbolicArcSine",
    "HyperbolicArcCosine",
    "HyperbolicArcTangent",
    "HyperbolicArcCosecant",
    "HyperbolicArcSecant",
    "HyperbolicArcCotangent",
    "sin",
    "cos",
    "tan",
    "arcsin",
    "arccos",
    "arctan",
    "asin",
    "acos",
    "atan",
    "csc",
    "sec",
    "cot",
    "arccsc",
    "arcsec",
    "arccot",
    "acsc",
    "asec",
    "acot",
    "sinh",
    "cosh",
    "tanh",
    "csch",
    "sech",
    "coth",
    "arcsinh",
    "arccosh",
    "arctanh",
    "arccsch",
    "arcsech",
    "arccoth",
    "asinh",
    "acosh",
    "atanh",
    "acsch",
    "asech",
    "acoth",
    "Logarithm",
    "NaturalLogarithm",
    "Exponential",
    "log",
    "ln",
    "exp",
    "Function",
    "FunctionGenerator",
    "Operator",
    "OperatorGenerator",
]

