"""Predefined Greek letters, mathematical constants, and punctuation literals."""

from .core import Literal, Macro
from .quantity import Variable


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

zero, one, two, three, four, five, six, seven, eight, nine = map(Literal, range(10))
inf = Macro("infty")
infinity = inf
infty = inf

# Punctuation & Spacing Literals
comma = Literal("\\,,")
period = Literal("\\,.")
newline = Literal("\\\\")
empty = Literal("")
alignment = Literal("&")
space = Literal("\\ ")
smallspace = Literal("\\,")


__all__ = [
    # Greek letters
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "varepsilon",
    "zeta",
    "eta",
    "theta",
    "vartheta",
    "iota",
    "kappa",
    "lambda_",
    "mu",
    "nu",
    "xi",
    "pi",
    "varpi",
    "rho",
    "varrho",
    "sigma",
    "varsigma",
    "tau",
    "upsilon",
    "phi",
    "varphi",
    "chi",
    "psi",
    "omega",
    "Gamma",
    "Delta",
    "Theta",
    "Lambda",
    "Xi",
    "Pi",
    "Sigma",
    "Upsilon",
    "Phi",
    "Psi",
    "Omega",
    # Constants & Digits
    "nabla",
    "i",
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "inf",
    "infinity",
    "infty",
    # Punctuation & Spacing Literals
    "comma",
    "period",
    "newline",
    "empty",
    "alignment",
    "space",
    "smallspace",
]
