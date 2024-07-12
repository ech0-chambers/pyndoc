from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Tuple
import pint

ureg = pint.UnitRegistry()
ureg.define("electronvolt = 1.602176634e-19 * joules = eV")

TARGET_FORMAT = None



@pint.register_unit_format("Ls")
def format_unit_simple(unit, registry, **options):
    return "\\ " + "\\,".join(f"\\mathrm{{{u}}}{('^{' + str(int(p)) + '}') if p != 1 else ''}" for u, p in unit.items())

def format_si_unit(units: str, html: bool = False) -> str:
    if html:
        output = f"{ureg.parse_expression(units).units:~Hs}"
        # output = re.sub(r"\bdeg\b", "&deg;", output)
        output = output.replace("deg", "&deg;")
        return output
    output = f"{ureg.parse_expression(units).units:~Ls}"
    output = re.sub(r"\bdeg\b", r"^{\\circ}", output)
    return output

prefixes = [
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

def siunit_html(units: str, inside_math: bool = False) -> str:
    # We're receiving a string in the siunitx format, like "\centi\meter\per\second\squared"
    # Need to transform into something like "centimeter per second squared"
    # check for any prefixes and join them to the unit
    # remove the backslashes

    for prefix in prefixes:
        units = re.sub(rf"\\{prefix}\\", prefix, units)
    
    # remove the backslashes
    units = units.replace("\\", " ")
    units = re.sub(r"\s+", " ", units)  # remove multiple spaces
    if inside_math:
        return format_si_unit(units)
    return "\(" + format_si_unit(units) + "\)"

MULTIPLICATION_OPERATOR = "\\times"
AUTO_TRUNCATE_LENGTH = 6

class Token(ABC):
    @abstractmethod
    def __str__(self):
        pass

    def __add__(self, other: Any) -> "Expression":
        return Add(self, other)

    def __radd__(self, other: Any) -> "Expression":
        return Add(other, self)

    def __sub__(self, other: Any) -> "Expression":
        return Subtract(self, other)

    def __rsub__(self, other: Any) -> "Expression":
        return Subtract(other, self)

    def __mul__(self, other: Any) -> "Expression":
        return Multiply(self, other)

    def __rmul__(self, other: Any) -> "Expression":
        return Multiply(other, self)

    def __pow__(self, other: Any) -> "Expression":
        return Power(self, other)

    def __rpow__(self, other: Any) -> "Expression":
        return Power(other, self)

    # Using @ for \times

    def __matmul__(self, other: Any) -> "Expression":
        return Times(self, other)

    def __rmatmul__(self, other: Any) -> "Expression":
        return Times(other, self)

    def __getitem__(self, other: Any) -> "Expression":
        """Using getitem to represent a subscript or index.

        Parameters
        ----------
        other : Any
            The subscript or index.

        Returns
        -------
        Expression
            The subscripted or indexed expression.
        """
        return Index(self, other)

    def __div__(self, other: Any) -> "Expression":
        return Divide(self, other)

    def __rdiv__(self, other: Any) -> "Expression":
        return Divide(other, self)

    def __truediv__(self, other: Any) -> "Expression":
        return Divide(self, other)

    def __rtruediv__(self, other: Any) -> "Expression":
        return Divide(other, self)

    # use `a // b` to force display fraction

    def __floordiv__(self, other: Any) -> "Expression":
        """Using `//` to force a display mode fraction (\\dfrac{}{})
        instead of an inline fraction (\\frac{}{}).

        Parameters
        ----------
        other : Any
            The denominator.

        Returns
        -------
        Expression
            The fraction.
        """
        return Divide(self, other, display=True)

    def __rfloordiv__(self, other: Any) -> "Expression":
        return Divide(other, self, display=True)

    def __pos__(self) -> "Expression":
        return Positive(self)

    def __neg__(self) -> "Expression":
        return Negative(self)

    def __eq__(self, other: Any) -> "Expression":
        return Equation(self, other)

    def __lt__(self, other: Any) -> "Expression":
        return LessThan(self, other)

    def __le__(self, other: Any) -> "Expression":
        return LessThanOrEqual(self, other)

    def __gt__(self, other: Any) -> "Expression":
        return GreaterThan(self, other)

    def __ge__(self, other: Any) -> "Expression":
        return GreaterThanOrEqual(self, other)

    def __ne__(self, other: Any) -> "Expression":
        return NotEqual(self, other)

    # Since we're using + as the binary plus operator even for strings, we'll use the bitwise `and` operator for concatenation. This should be unlikely to cause any issues in normal use.

    def __and__(self, other: Any) -> str:
        """Using `&` to concatenate two expressions, since `+` is used for addition.

        Parameters
        ----------
        other : Any
            The other expression to concatenate.

        Returns
        -------
        str
            The concatenated expression. Note this is no longer an Expression object.
        """
        return f"{self} {other}"

    def __rand__(self, other: Any) -> str:
        return f"{other} {self}"

    def __hash__(self) -> int:
        return hash(str(self))

    @abstractmethod
    def __call__():
        pass

class NonCallableToken(Token):
    def __call__(self) -> str:
        return str(self)

class Literal(Token):
    def __init__(self, expr: Any):
        self.expr = expr

    def __str__(self) -> str:
        return str(self.expr)

    def __call__(self) -> str:
        return self.expr


failed_conversion = Literal(r"\text{\color{red}None}")

def format_value(value: float | None, fmt: str | None, unit: str | None) -> str:
    if value is None:
        return failed_conversion
    if fmt is None:
        print_value = str(value)
        if AUTO_TRUNCATE_LENGTH > 0 and "." in print_value and len(print_value.split(".")[1]) > AUTO_TRUNCATE_LENGTH:
            # assume this is a floating point rounding error and truncate, then strip trailing zeros
            integer, decimal = print_value.split(".")
            decimal = decimal[:6]
            decimal = decimal.rstrip("0")
            print_value = f"{integer}.{decimal}"
            print_value = print_value.rstrip(".") # if the decimal is empty, remove the dot
        if unit is None:
            return Literal(print_value)
        if TARGET_FORMAT.name.lower() in ["latex", "beamer"]:
            return Macro("SI", print_value, unit)
        if TARGET_FORMAT.name.lower() in ["html", "chunkedhtml", "revealjs"]:
            unit = siunit_html(unit, True)
            return f"{print_value} {unit}"
        return f"{print_value} {unit}"
    latex = False
    if "el" in fmt.lower() and unit is None:
        latex = True
        fmt = fmt.lower().replace("el", "e")
    if "e" in fmt.lower() and TARGET_FORMAT.name.lower() not in ["latex", "beamer"]:
        latex = True
    print_value = f"{value:{fmt}}"
    if latex:
        left, right = print_value.lower().split("e")
        right = str(int(right)) # remove leading zeros and + sign
        print_value = f"{left} \\times 10^{{{right}}}"
    if unit is None:
        return Literal(print_value)
    if TARGET_FORMAT.name.lower() in ["latex", "beamer"]:
        return Macro("SI", print_value, unit)
    if TARGET_FORMAT.name.lower() in ["html", "chunkedhtml", "revealjs"]:
        unit = siunit_html(unit, True)
        return f"{print_value} {unit}"
    return f"{print_value} {unit}"


class Expression(Token, ABC):
    def __init__(self, value: Any = None):
        if isinstance(value, Expression):
            value = float(value)
            if value.is_integer():
                value = int(value)
        self.value = value

    def __call__(self, format: str = None, unit: str = None) -> str:
        return format_value(self.value, format, unit)

    def __str__(self) -> str:
        return str(self.value)
    
    def __float__(self) -> float | None:
        # I'm not sure if we should be returning None here or not, but it should throw an error if it's used in a context where a float is expected. This is probably a good thing?
        if self.value is None:
            return None
        if isinstance(self.value, int):
            return float(self.value)
        if isinstance(self.value, float):
            return self.value
        try:
            return float(str(self.value))
        except ValueError:
            return None
        
    def __int__(self) -> int:
        value = self.__float__()
        if value is None:
            return None
        return int(value)


class Variable(Expression):
    def __init__(self, identifier: str, value: Any = None):
        super().__init__(value)
        self.identifier = identifier

    def __str__(self) -> str:
        return self.identifier
    
class Argument:
    def __init__(
        self,
        arg: str | Token | Dict[str, Any],
        is_optional: bool = False,
        in_expl3: bool = False,
    ):
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


class Macro(NonCallableToken):
    def __init__(self, name: str, *arguments, in_expl3: bool = False):
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


class Environment(NonCallableToken):
    def __init__(
        self,
        name: str,
        *arguments,
        content: str | Token | List[Token] = None,
        in_expl3: bool = False,
    ):
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


class _Container(Expression):
    def __init__(self, *children: str | Token):
        if not isinstance(children, (list, tuple)):
            children = [children]
        else:
            # Flatten nested lists if there's only one item
            while len(children) == 1 and isinstance(children[0], (list, tuple)):
                children = children[0]
        children = [
            (
                expr
                if isinstance(expr, Token)
                else (
                    _Container(expr)
                    if isinstance(expr, (list, tuple))
                    else Literal(expr)
                )
            )
            for expr in children
        ]
        self.children = children
        if len(children) == 1:
            self.value = children[0].value
        else:
            self.value = None # We set this to None because the `value` could be ambiguous

    def __str__(self) -> str:
        return "".join([str(child) for child in self.children])

    def __getitem__(self, index: int) -> Expression:
        return self.children[index]
    
    def __call__(self, format: str = None, unit: str = None) -> str:
        return None

class Sequence(_Container):
    def __init__(self, *children: str | Token):
        super().__init__(*children)

    def __str__(self) -> str:
        return ", ".join([str(child) for child in self.children])

    def __getitem__(self, index: int) -> Token:
        return self.children[index]

class Bracket(_Container):
    def __init__(
        self, children: str | Token | List[Token], scale: bool = False
    ):
        super().__init__(children)
        self.left_delim = "("
        self.right_delim = ")"
        self.scale = scale

    def __str__(self) -> str:
        scale_left, scale_right = "\\left", "\\right"
        return f"{scale_left if self.scale else ''}{self.left_delim}{super().__str__()}{scale_right if self.scale else ''}{self.right_delim}"


class SquareBracket(Bracket):
    def __init__(self, children: str | Token | List[Token], scale: bool = False):
        super().__init__(children, scale)
        self.left_delim = "["
        self.right_delim = "]"


class CurlyBracket(Bracket):
    def __init__(self, children: str | Token | List[Token], scale: bool = False):
        super().__init__(children, scale)
        self.left_delim = "\\lbrace"
        self.right_delim = "\\rbrace"


class AngleBracket(Bracket):
    def __init__(self, children: str | Token | List[Token], scale: bool = False):
        super().__init__(children, scale)
        self.left_delim = "\\langle"
        self.right_delim = "\\rangle"


class Absolute(Bracket):
    def __init__(self, children: str | Token | List[Token], scale: bool = False):
        super().__init__(children, scale)
        self.left_delim = "\\lvert"
        self.right_delim = "\\rvert"

    def __float__(self):
        if len(self.children) != 1:
            return None
        return abs(float(self.children[0]))

    def __int__(self):
        if len(self.children) != 1:
            return None
        return abs(int(self.children[0]))
    
    def __call__(self, format: str | None = None, unit: str | None = None, show_brackets: bool = False):
        if len(self.children) != 1:
            return failed_conversion
        child = self.children[0]
        if show_brackets:
            return f"\\left|{child(format, unit)}\\right|"
        if float(child) is None:
            return failed_conversion
        child_value = abs(float(child))
        return var("", child_value)(format, unit)


class _UnaryOperator(Expression):
    def __init__(self, operator: str, operand: Token, group: bool = False):
        self.operator = operator
        self.operand = operand
        self.group = group

    def __str__(self) -> str:
        if self.group:
            return f"{self.operator}{{{self.operand}}}"
        return f"{self.operator}{self.operand}"
    
    def get_value(self) -> Any | None:
        if self.operand.value is None:
            return None
        value = (
            self.operand.value.expr
            if isinstance(self.operand.value, Literal)
            else self.operand.value
        )
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                return None
        if not isinstance(value, (float, int)):
            return None
    
        if not isinstance(value, int) and value.is_integer():
            value = int(value)

        return value
    
    def calc_value(self):
        return None # should be implemented in subclasses

class Positive(_UnaryOperator):
    def __init__(self, operand: Token):
        super().__init__("+", operand)
        self.value = self.calc_value()

    def calc_value(self) -> Any:
        # should this return abs? or should it just return the value?
        value = self.get_value()
        if value is None:
            return None
        return value

    def __call__(self, format: str = None, unit: str = None) -> str:
        value = self.calc_value()
        return format_value(value, format, unit)
    
class Negative(_UnaryOperator):
    def __init__(self, operand: Token):
        super().__init__("-", operand)
        self.value = self.calc_value()

    def calc_value(self) -> Any:
        value = self.get_value()
        if value is None:
            return None
        return -value

    def is_integer(self):
        return float(self.operand).is_integer()

    def __call__(self, format: str = None, unit: str = None) -> str:
        value = self.calc_value()
        return format_value(value, format, unit)
    
    def __float__(self):
        value = self.calc_value()
        if value is None:
            return None
        return float(value)

class Subscript(_UnaryOperator):
    def __init__(self, operand: Token):
        super().__init__("_", operand, group = True)
    
    def calc_value(self) -> Any:
        return None

    def __call__(self, format: str = None, unit: str = None) -> Literal:
        return Literal(f"{{}}_{{{self.operand(format, unit)}}}")
    
class Superscript(_UnaryOperator):
    def __init__(self, operand: Token):
        super().__init__("^", operand, group = True)
    
    def calc_value(self) -> Any:
        return None

    def __call__(self, format: str = None, unit: str = None) -> Literal:
        return Literal(f"{{}}^{{{self.operand(format, unit)}}}")

def as_expression(expr: Any) -> Expression:
    if isinstance(expr, tuple):
        if len(expr) == 1:
            return Bracket(as_expression(expr[0]))
        return Sequence([as_expression(ei) for ei in expr])
    if isinstance(expr, list):
        if len(expr) == 1:
            return SquareBracket(as_expression(expr[0]))
        return Sequence([as_expression(ei) for ei in expr])
    if isinstance(expr, set):
        if len(expr) == 1:
            return CurlyBracket(as_expression(list(expr)[0]))
        return Sequence([as_expression(ei) for ei in list(expr)])
    if not isinstance(expr, Token):
        if isinstance(expr, (float, int)):
            value = expr
        elif isinstance(expr, str):
            try:
                value = float(expr)
            except ValueError:
                value = expr
        expr = Expression(value)
    if not isinstance(expr, Expression):
        expr = Expression(expr)
    return expr


class _BinaryOperator(Expression):
    def __init__(
        self,
        operator: str,
        left: Token | Any,
        right: Token | Any,
        group_left: bool = False,
        group_right: bool = False,
    ):
        self.operator = operator
        self.left = as_expression(left)
        self.right = as_expression(right)
        self.group_left = group_left
        self.group_right = group_right
        self.value = self.calc_value()

    def get_left_right_values(self) -> Tuple[Any, Any] | None:
        if self.left.value is None or self.right.value is None:
            return None, None
        left_value = (
            self.left.value.expr
            if isinstance(self.left.value, Literal)
            else self.left.value
        )
        right_value = (
            self.right.value.expr
            if isinstance(self.right.value, Literal)
            else self.right.value
        )
        
        if isinstance(left_value, (str, Expression)):
            try:
                left_value = float(left_value)
            except ValueError:
                return None, None
        if isinstance(right_value, (str, Expression)):
            try:
                right_value = float(right_value)
            except ValueError:
                return None, None
        
        if isinstance(left_value, float) and left_value.is_integer():
            left_value = int(left_value)
        if isinstance(right_value, float) and right_value.is_integer():
            right_value = int(right_value)

        if not isinstance(left_value, (float, int)):
            return None, None
        if not isinstance(right_value, (float, int)):
            return None, None
        return left_value, right_value

    def calc_value(self) -> Any:
        return None  # should be implemented in subclasses

    def __str__(self) -> str:
        left = f"{{{self.left}}}" if self.group_left else str(self.left)
        right = f"{{{self.right}}}" if self.group_right else str(self.right)
        return f"{left} {self.operator} {right}".replace("  ", " ")


class Add(_BinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__("+", left, right)

    def calc_value(self) -> Any:
        left, right = self.get_left_right_values()
        if left is None or right is None:
            return None
        return left + right


class Subtract(_BinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__("-", left, right)

    def calc_value(self) -> Any:
        left, right = self.get_left_right_values()
        if left is None or right is None:
            return None
        return left - right


class Multiply(_BinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__("", left, right)

    def calc_value(self) -> Any:
        left, right = self.get_left_right_values()
        if left is None or right is None:
            return None
        return left * right


class Times(_BinaryOperator):
    # Like multiply, but explicitly uses the multiplication symbol
    def __init__(self, left: Token, right: Token):
        super().__init__(MULTIPLICATION_OPERATOR, left, right)

    def calc_value(self) -> Any:
        left, right = self.get_left_right_values()
        if left is None or right is None:
            return None
        return left * right


class Divide(_BinaryOperator):
    def __init__(self, left: Token, right: Token, display: bool = False):
        super().__init__("/", left, right)
        self.display = display

    def __str__(self) -> str:
        if self.display:
            return f"\\dfrac{{{self.left}}}{{{self.right}}}"
        return f"\\frac{{{self.left}}}{{{self.right}}}"

    def calc_value(self) -> Any:
        left, right = self.get_left_right_values()
        if left is None or right is None:
            return None
        result = left / right
        # if it's an integer, convert it to an int
        if result.is_integer():
            result = int(result)
        return result


class Power(_BinaryOperator):
    def __init__(self, left: Token, right: Token):
        group_left = not isinstance(left, Index)
        super().__init__("^", left, right, group_left=group_left, group_right=True)

    def calc_value(self) -> Any:
        left, right = self.get_left_right_values()
        if left is None or right is None:
            return None
        return left**right


class Index(_BinaryOperator):
    def __init__(self, left: Token, right: Token):
        group_left = not isinstance(left, Power)
        super().__init__("_", left, right, group_left=group_left, group_right=True)

    def calc_value(self) -> Any:
        left, right = self.get_left_right_values()
        if left is None or right is None:
            return None
        return left  # This should be used purely for display purposes, so we shouldn't change the value. Maybe we should always return None here?

class _NonValuedBinaryOperator(_BinaryOperator):
    def calc_value(self) -> Any:
        return None


class Equation(_NonValuedBinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__("=", left, right)

class LessThan(_NonValuedBinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__("<", left, right)

class GreaterThan(_NonValuedBinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__(">", left, right)

class LessThanOrEqual(_NonValuedBinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__("\\leq", left, right)

class GreaterThanOrEqual(_NonValuedBinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__("\\geq", left, right)

class NotEqual(_NonValuedBinaryOperator):
    def __init__(self, left: Token, right: Token):
        super().__init__("\\neq", left, right)

class LimitsExpression(Expression):
    def __init__(self, function: Macro | str, expr: Token | Any, lower: Token | Any = None, upper: Token | Any = None):
        self.value = None
        if isinstance(function, str):
            function = Macro(function)
        self.function = function
        self.lower = None if lower is None else as_expression(lower)
        self.upper = None if upper is None else as_expression(upper)
        self.expr = as_expression(expr)

    def __str__(self) -> str:
        if self.lower is None and self.upper is None:
            return f"{self.function}{self.expr}"
        if self.lower is None:
            return f"{self.function}\\limits^{{{self.upper}}}{self.expr}"
        if self.upper is None:
            return f"{self.function}\\limits_{{{self.lower}}}{self.expr}"
        return f"{self.function}\\limits_{{{self.lower}}}^{{{self.upper}}}{self.expr}"

# class Integral(LimitsExpression):
#     def __init__(self, expr: Token | Any, int_var: Token | Any, lower: Token | Any = None, upper: Token | Any = None):
#         super().__init__("int", expr, lower, upper)
#         if not isinstance(int_var, Token):
#             int_var = Literal(int_var)
#         self.int_var = int_var

#     def __str__(self) -> str:
#         return super().__str__() + f"\\,\\mathrm{{d}}{self.int_var}"

# == LaTeX Math Macros ==

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
pi = Macro("pi")
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

# Common Math Macros

def power(base: str | Token, exponent: str | Token) -> str:
    return Power(base, exponent)

def index(base: str | Token, subscript: str | Token) -> str:
    return Index(base, subscript)

def math_sup(exponent: str | Token) -> str:
    return Power("", exponent)

def math_sub(subscript: str | Token) -> str:
    return Subscript(subscript)

def sqrt(expr: str | Token, nroot: int = None) -> Macro:
    args = []
    if nroot:
        args.append((True, nroot))
    args.append(expr)
    return Macro("sqrt", *args)

def frac(numerator: str | Token, denominator: str | Token) -> str:
    return Divide(numerator, denominator)

def dfrac(numerator: str | Token, denominator: str | Token) -> str:
    return Divide(numerator, denominator, display = True)

def dot(expr: str | Token) -> str:
    return Macro("dot", expr)

def ddot(expr: str | Token) -> str:
    return Macro("ddot", expr)

def hat(expr: str | Token) -> str:
    return Macro("hat", expr)

def bar(expr: str | Token) -> str:
    return Macro("bar", expr)

def vec(expr: str | Token) -> str:
    return Macro("vec", expr)

def tilde(expr: str | Token) -> str:
    return Macro("tilde", expr)

def widehat(expr: str | Token) -> str:
    return Macro("widehat", expr)

def overline(expr: str | Token) -> str:
    return Macro("overline", expr)

def widetilde(expr: str | Token) -> str:
    return Macro("widetilde", expr)

class _Trig_Function(NonCallableToken):
    # Not all of these are actually trig functions, but I don't know what else to call them
    def __init__(self, name: str, expr: str | Token, power: Any = None):
        self.name = name
        
        self.expr = as_expression(expr)

        self.power = None if power is None else as_expression(power)

    def __str__(self) -> str:
        if self.power is None:
            return _Container(Macro(self.name), Bracket(self.expr, scale = True)).__str__()
        return _Container(Power(Macro(self.name), self.power), Bracket(self.expr, scale = True)).__str__()

def sin(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("sin", expr, power)

def cos(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("cos", expr, power)

def tan(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("tan", expr, power)

def csc(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("csc", expr, power)

def sec(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("sec", expr, power)

def cot(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("cot", expr, power)

def exp(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("exp", expr, power)

def log(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("log", expr, power)

def ln(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("ln", expr, power)

def lg(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("lg", expr, power)

def sinh(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("sinh", expr, power)

def cosh(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("cosh", expr, power)

def tanh(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("tanh", expr, power)

def coth(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("coth", expr, power)

def arcsin(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("arcsin", expr, power)

def arccos(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("arccos", expr, power)

def arctan(expr: str | Token, power: Any = None) -> str:
    return _Trig_Function("arctan", expr, power)

def supsub(base: str | Token, superscript: str | Token, subscript: str | Token) -> str:
    return _BinaryOperator("_", _BinaryOperator("^", base, superscript, group_left = True, group_right = True), subscript, group_right = True)

def bracket(expr: str | Token, scale: bool = False) -> str:
    return Bracket(expr, scale)

paren = bracket

def square_bracket(expr: str | Token, scale: bool = False) -> str:
    return SquareBracket(expr, scale)

def curly_bracket(expr: str | Token, scale: bool = False) -> str:
    return CurlyBracket(expr, scale)

brace = curly_bracket

def absolute(expr: str | Token, scale: bool = True) -> str:
    return Absolute(expr, scale)

def angle_bracket(expr: str | Token, scale: bool = False) -> str:
    return AngleBracket(expr, scale)

def sum(expr: str | Token, lower: str | Token = None, upper: str | Token = None) -> str:
    return LimitsExpression("sum", expr, lower, upper)

# def integral(expr: str | Token, int_var: str | Token, lower: str | Token = None, upper: str | Token = None) -> str:
#     return Integral(expr, int_var, lower, upper)


sym = as_expression

var = Variable

def split(lines: List[str | Token | Tuple[str | Token]], environment = "split") -> str:
    if not isinstance(lines, (list, tuple)):
        lines = [lines]
    for i, line in enumerate(lines):
        if isinstance(line, (list, tuple)):
            lines[i] = " & ".join([str(expr) for expr in line])
        else:
            lines[i] = str(line)
    return f"\\begin{{{environment}}}\n\t" + "\\\\\n\t".join(lines) + f"\n\\end{{{environment}}}"

# def function(name: str | Token, *args: str | Token) -> str:
#     if len(args) == 1:
#         return literal(name) * (literal(args[0]), )
#     return literal(name) * Bracket(literal(args), scale = True)


# def fmt(expr: str | Token, format: str) -> str:
#     return literal(expr, format)


# empty = Literal("")

alignment = Literal("&")

def __pythonify_name(name: str) -> str:
    # convert a string into a valid python variable name
    replacements = [
        (" ", "_"),
        ("-","_"),
        ("\\", ""),
    ]
    for old, new in replacements:
        name = name.replace(old, new)
    if not name[0].isalpha():
        name = "_" + name
    for c in name:
        if not c.isalnum() and c != "_":
            name = name.replace(c, "")
    return name

def define_symbols(statements: str, namespace: dict | None = None) -> None:
    # This is absolutely not safe, but anyone with access to this function has access to the entire python environment anyway
    statements_list = statements.split("\n")
    statements_list = [stmt.split(";") for stmt in statements_list]
    # collapse the list to 1d
    statements_list = [stmt.strip() for stmts in statements_list for stmt in stmts]
    # remove comments which start with #
    statements_list = [stmt.split("#")[0].strip() for stmt in statements_list]
    # remove empty lines
    statements_list = [stmt for stmt in statements_list if stmt]
    assignments = []
    for statement in statements_list:
        if not "=" in statement:
            new_name = __pythonify_name(statement)
            if namespace is not None and new_name in namespace:
                raise ValueError(f"Symbol {new_name} already defined")
            new_symbol = as_expression(statement)
            if namespace is not None:
                namespace[new_name] = new_symbol
            assignments.append(new_symbol)
            continue
        name, value = statement.split("=")
        name = name.strip()
        value = value.strip()
        matched = re.match(r"(\"|\').*?(\1)", value)
        if matched:
            value = value[1:-1]
        new_name = __pythonify_name(name)
        if namespace is not None and new_name in namespace:
            raise ValueError(f"Symbol {new_name} already defined")
        new_symbol = Variable(name, value)
        if namespace is not None:
            namespace[new_name] = new_symbol
        assignments.append(new_symbol)
    return assignments

symbols = define_symbols