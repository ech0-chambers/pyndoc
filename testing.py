import latex as tex
from formats import Format
tex.TARGET_FORMAT = Format.LATEX

import scipy.constants as const
n = tex.var("n", 3)
Z = tex.var("Z", 1)
mu = tex.var(r"\mu", (const.m_e * const.m_p) / (const.m_e + const.m_p))
k = tex.var("k", 4 * const.pi * const.epsilon_0)
hbar = tex.var("\\hbar", const.hbar)
e = tex.var("e", const.e)
E = tex.var("E", -mu.value * Z.value ** 2 * e.value ** 4 / (2 * k.value **2 * hbar.value **2) * Z.value / n.value ** 2)

def split_equals(lines):
    if len(lines) <= 1:
        return tex.split(lines)
    return tex.split([lines[0]] + [tex.alignment == line for line in lines[1:]])

def hydrogen(level, ev: bool = False):
    E = -mu.value * e.value ** 4 / (2 * k.value **2 * hbar.value **2) / level ** 2
    if ev:
        return tex.var("E", E / const.e)
    return tex.var("E", E)



E0 = tex.var("E_0", hydrogen(1, True))
dE = tex.var("\\Delta E", hydrogen(1) - hydrogen(3))
h = tex.var("h", const.h)
c = tex.var("c", const.c)
wavelength = tex.var("\\lambda", h * c / dE * 1e9)


print((-(E  - hydrogen(1)) / const.e)('.2f', '\\electronvolt'))