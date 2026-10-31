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
partial = Macro("partial")
hbar = Macro("hbar")
i = Literal("i")

zero, one, two, three, four, five, six, seven, eight, nine = map(Literal, range(10))
inf = Macro("infty")
infinity = inf
infty = inf

# Multiplication, Arithmetic & Relational Symbols
cdot = Macro("cdot")
pm = Macro("pm")
plusminus = pm
mp = Macro("mp")
minusplus = mp
times = Macro("times")
propto = Macro("propto")
sim = Macro("sim")
ll = Macro("ll")
gg = Macro("gg")
implies = Macro("implies")
iff = Macro("iff")

# Ellipses
dots = Macro("dots")
ldots = Macro("ldots")
cdots = Macro("cdots")
vdots = Macro("vdots")
ddots = Macro("ddots")

# Logic & Set Theory
forall = Macro("forall")
exists = Macro("exists")
in_ = Macro("in")
notin = Macro("notin")
subset = Macro("subset")
subseteq = Macro("subseteq")
cap = Macro("cap")
cup = Macro("cup")

# Standard Number Sets
RR = Macro("mathbb", "R")
Reals = RR
CC = Macro("mathbb", "C")
Complexes = CC
ZZ = Macro("mathbb", "Z")
Integers = ZZ
NN = Macro("mathbb", "N")
Naturals = NN
QQ = Macro("mathbb", "Q")
Rationals = QQ

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
    "partial",
    "hbar",
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
    # Arithmetic & Relational Symbols
    "cdot",
    "pm",
    "plusminus",
    "mp",
    "minusplus",
    "times",
    "propto",
    "sim",
    "ll",
    "gg",
    "implies",
    "iff",
    # Ellipses
    "dots",
    "ldots",
    "cdots",
    "vdots",
    "ddots",
    # Logic & Set Theory
    "forall",
    "exists",
    "in_",
    "notin",
    "subset",
    "subseteq",
    "cap",
    "cup",
    # Standard Number Sets
    "RR",
    "Reals",
    "CC",
    "Complexes",
    "ZZ",
    "Integers",
    "NN",
    "Naturals",
    "QQ",
    "Rationals",
    # Punctuation & Spacing Literals
    "comma",
    "period",
    "newline",
    "empty",
    "alignment",
    "space",
    "smallspace",
]
