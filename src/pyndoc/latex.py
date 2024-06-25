from abc import ABC, abstractmethod
from typing import Any, Dict, List


class Expression(ABC):
    @abstractmethod
    def __str__(self):
        pass

    def __add__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Add(self, other)
        return Add(self, literal(other))

    def __radd__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Add(other, self)
        return Add(literal(other), self)

    def __sub__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Subtract(self, other)
        return Subtract(self, literal(other))

    def __rsub__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Subtract(other, self)
        return Subtract(literal(other), self)

    def __mul__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Multiply(self, other)
        return Multiply(self, literal(other))

    def __rmul__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Multiply(other, self)
        return Multiply(literal(other), self)

    def __pow__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Power(self, other)
        return Power(self, literal(other))
    
    def __rpow__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Power(other, self)
        return Power(literal(other), self)
    
    # Using @ for \times

    def __matmul__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Times(self, other)
        return Times(self, literal(other))
    
    def __rmatmul__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Times(other, self)
        return Times(literal(other), self)

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
        if isinstance(other, Expression):
            return Index(self, other)
        if isinstance(other, (list, tuple)):
            return Index(self, Sequence(other))
        return Index(self, literal(other))

    def __div__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Divide(self, other)
        return Divide(self, literal(other))

    def __rdiv__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Divide(other, self)
        return Divide(literal(other), self)

    def __truediv__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Divide(self, other)
        return Divide(self, literal(other))

    def __rtruediv__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Divide(other, self)
        return Divide(literal(other), self)
    
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
        if isinstance(other, Expression):
            return Divide(self, other, display = True)
        return Divide(self, literal(other), display = True)

    def __rfloordiv__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Divide(other, self, display = True)
        return Divide(literal(other), self, display = True)

    def __pos__(self) -> "Expression":
        return _UnaryOperator("+", self)
    
    def __neg__(self) -> "Expression":
        return _UnaryOperator("-", self)
    
    def __eq__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return Equation(self, other)
        return Equation(self, literal(other))
    
    def __lt__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return LessThan(self, other)
        return LessThan(self, literal(other))
    
    def __le__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return LessThanOrEqual(self, other)
        return LessThanOrEqual(self, literal(other))
    
    def __gt__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return GreaterThan(self, other)
        return GreaterThan(self, literal(other))
    
    def __ge__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return GreaterThanOrEqual(self, other)
        return GreaterThanOrEqual(self, literal(other))
    
    def __ne__(self, other: Any) -> "Expression":
        if isinstance(other, Expression):
            return NotEqual(self, other)
        return NotEqual(self, literal(other))
    
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


class Literal(Expression):
    def __init__(self, value: Any, format: str = None):
        self.value = value
        self.format = format

    def __str__(self) -> str:
        if self.format:
            return f"{self.value:{self.format}}"
        return str(self.value)

def literal(value: Any, format: str = None) -> str | Expression:
    """Create a Literal object.

    Parameters
    ----------
    value : Any
        The value to be converted to a Literal object.
    format : str, optional
        The format string to format the value, by default None

    Returns
    -------
    str | Expression
        The Literal object.        
    """    
    if isinstance(value, Expression):
        return value
    if isinstance(value, list):
        if len(value) == 1:
            return SquareBracket(value[0], scale = True)
        return Sequence(value)
    if isinstance(value, tuple):
        if len(value) == 1:
            return Bracket(value[0], scale = True)
        return Sequence(value)
    if isinstance(value, set):
        if len(value) == 1:
            return CurlyBracket(list(value)[0], scale = True)
        return Sequence(list(value))
    return Literal(value, format)

value = literal

class Argument:
    def __init__(
        self,
        arg: str | Expression | Dict[str, Any],
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


class Macro(Expression):
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


class Environment(Expression):
    def __init__(
        self,
        name: str,
        *arguments,
        content: str | Expression | List[Expression] = None,
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
    def __init__(self, *children: str | Expression):
        if not isinstance(children, (list, tuple)):
            children = [children]
        else:
            # Flatten nested lists if there's only one item1
            while len(children) == 1 and isinstance(children[0], (list, tuple)):
                children = children[0]
        children = [
            (
                expr
                if isinstance(expr, Expression)
                else (
                    _Container(expr)
                    if isinstance(expr, (list, tuple))
                    else Literal(expr)
                )
            )
            for expr in children
        ]
        self.children = children

    def __str__(self) -> str:
        return "".join([str(child) for child in self.children])
    
    # def __getitem__(self, index: int) -> Expression:
    #     return self.children[index]

class Sequence(_Container):
    def __init__(self, *children: str | Expression):
        super().__init__(*children)

    def __str__(self) -> str:
        return ", ".join([str(child) for child in self.children])

class Bracket(_Container):
    def __init__(
        self, children: str | Expression | List[Expression], scale: bool = False
    ):
        super().__init__(children)
        self.left_delim = "("
        self.right_delim = ")"
        self.scale = scale

    def __str__(self) -> str:
        scale_left, scale_right = "\\left", "\\right"
        return f"{scale_left if self.scale else ''}{self.left_delim}{super().__str__()}{scale_right if self.scale else ''}{self.right_delim}"


class SquareBracket(Bracket):
    def __init__(self, children: str | Expression | List[Expression], scale: bool = False):
        super().__init__(children, scale)
        self.left_delim = "["
        self.right_delim = "]"


class CurlyBracket(Bracket):
    def __init__(self, children: str | Expression | List[Expression], scale: bool = False):
        super().__init__(children, scale)
        self.left_delim = "\\lbrace"
        self.right_delim = "\\rbrace"


class AngleBracket(Bracket):
    def __init__(self, children: str | Expression | List[Expression], scale: bool = False):
        super().__init__(children, scale)
        self.left_delim = "\\langle"
        self.right_delim = "\\rangle"


class _UnaryOperator(Expression):
    def __init__(self, operator: str, operand: Expression, group: bool = False):
        self.operator = operator
        self.operand = operand
        self.group = group

    def __str__(self) -> str:
        if self.group:
            return f"{self.operator}{{{self.operand}}}"
        return f"{self.operator}{self.operand}"


class _BinaryOperator(Expression):
    def __init__(
        self,
        operator: str,
        left: Expression,
        right: Expression,
        group_left: bool = False,
        group_right: bool = False,
    ):
        self.operator = operator
        self.left = left
        self.right = right
        self.group_left = group_left
        self.group_right = group_right

    def __str__(self) -> str:
        left = f"{{{self.left}}}" if self.group_left else str(self.left)
        right = f"{{{self.right}}}" if self.group_right else str(self.right)
        return f"{left} {self.operator} {right}".replace("  ", " ")


class Add(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__("+", left, right)


class Subtract(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__("-", left, right)


class Multiply(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__("", left, right)


class Times(_BinaryOperator):
    # Like multiply, but explicitly uses the multiplication symbol
    def __init__(self, left: Expression, right: Expression):
        super().__init__("\\times", left, right)


class Divide(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression, display: bool = False):
        super().__init__("/", left, right)
        self.display = display

    def __str__(self) -> str:
        if self.display:
            return f"\\dfrac{{{self.left}}}{{{self.right}}}"
        return f"\\frac{{{self.left}}}{{{self.right}}}"


class Power(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        group_left = not isinstance(left, Index)
        super().__init__("^", left, right, group_left = group_left, group_right = True)

class Index(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        group_left = not isinstance(left, Power)
        super().__init__("_", left, right, group_left = group_left, group_right = True)

class Equation(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__("=", left, right)

class LessThan(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__("<", left, right)

class GreaterThan(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__(">", left, right)

class LessThanOrEqual(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__("\\leq", left, right)

class GreaterThanOrEqual(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__("\\geq", left, right)

class NotEqual(_BinaryOperator):
    def __init__(self, left: Expression, right: Expression):
        super().__init__("\\neq", left, right)


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
lambda_ = Macro("lambda_")
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

def power(base: str | Expression, exponent: str | Expression) -> str:
    return Power(base, exponent)

def index(base: str | Expression, subscript: str | Expression) -> str:
    return Index(base, subscript)

def math_sup(exponent: str | Expression) -> str:
    return Power("", exponent)

def math_sub(subscript: str | Expression) -> str:
    return _UnaryOperator("_", subscript, group = True)

def sqrt(expr: str | Expression, nroot: int = None) -> str:
    args = []
    if nroot:
        args.append((True, nroot))
    args.append(expr)
    return Macro("sqrt", *args)

def frac(numerator: str | Expression, denominator: str | Expression) -> str:
    return Divide(numerator, denominator)

def dfrac(numerator: str | Expression, denominator: str | Expression) -> str:
    return Divide(numerator, denominator, display = True)

def dot(expr: str | Expression) -> str:
    return Macro("dot", expr)

def ddot(expr: str | Expression) -> str:
    return Macro("ddot", expr)

def hat(expr: str | Expression) -> str:
    return Macro("hat", expr)

def bar(expr: str | Expression) -> str:
    return Macro("bar", expr)

def vec(expr: str | Expression) -> str:
    return Macro("vec", expr)

def tilde(expr: str | Expression) -> str:
    return Macro("tilde", expr)

def widehat(expr: str | Expression) -> str:
    return Macro("widehat", expr)

def overline(expr: str | Expression) -> str:
    return Macro("overline", expr)

def widetilde(expr: str | Expression) -> str:
    return Macro("widetilde", expr)

class _Trig_Function(Expression):
    # Not all of these are actually trig functions, but I don't know what else to call them
    def __init__(self, name: str, expr: str | Expression, power: Any = None):
        self.name = name
        if isinstance(expr, Expression):
            self.expr = expr
        else:
            self.expr = Literal(expr)
        self.power = power

    def __str__(self) -> str:
        if self.power is None:
            return _Container(Macro(self.name), Bracket(self.expr, scale = True)).__str__() 
        return _Container(Power(Macro(self.name), self.power), Bracket(self.expr, scale = True)).__str__()
    
def sin(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("sin", expr, power)

def cos(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("cos", expr, power)

def tan(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("tan", expr, power)

def csc(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("csc", expr, power)

def sec(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("sec", expr, power)

def cot(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("cot", expr, power)

def exp(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("exp", expr, power)

def log(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("log", expr, power)

def ln(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("ln", expr, power)

def lg(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("lg", expr, power)

def sinh(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("sinh", expr, power)

def cosh(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("cosh", expr, power)

def tanh(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("tanh", expr, power)

def coth(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("coth", expr, power)

def arcsin(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("arcsin", expr, power)

def arccos(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("arccos", expr, power)

def arctan(expr: str | Expression, power: Any = None) -> str:
    return _Trig_Function("arctan", expr, power)

def supsub(base: str | Expression, superscript: str | Expression, subscript: str | Expression) -> str:
    return _BinaryOperator("_", _BinaryOperator("^", base, superscript, group_left = True, group_right = True), subscript, group_right = True)

def bracket(expr: str | Expression, scale: bool = False) -> str:
    return Bracket(expr, scale)

paren = bracket

def square_bracket(expr: str | Expression, scale: bool = False) -> str:
    return SquareBracket(expr, scale)

def curly_bracket(expr: str | Expression, scale: bool = False) -> str:
    return CurlyBracket(expr, scale)

brace = curly_bracket

def angle_bracket(expr: str | Expression, scale: bool = False) -> str:
    return AngleBracket(expr, scale)

sym = literal