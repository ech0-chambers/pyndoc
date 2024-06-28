import periodictable as pt
import numpy as np


def format_element(
    symbol: str, mass: int, atomic_number: int = None, charge: int = None
) -> str:
    return (
        (f"_{{{atomic_number}}}" if atomic_number is not None else "")
        + f"^{{{mass}}}\\text{{{symbol}}}"
        + (f"^{{{charge:+d}}}" if charge is not None else "")
    )


def element_string(
    el_name: str,
    atomic_number: int = None,
    iso: int = None,
    show_atomic_number: bool = True,
) -> str:
    import periodictable as pt

    if atomic_number is not None:
        el = pt.elements[int(atomic_number)]
    else:
        el = pt.elements.symbol(el_name)
    if iso is None:
        iso = el.isotopes[np.argmax([el[iso].abundance for iso in el.isotopes])]
    if show_atomic_number:
        return format_element(el.symbol, iso, atomic_number=el.number)
    else:
        return format_element(el.symbol, iso)


def element(
    el_name: str,
    atomic_number: int = None,
    iso: int = None,
    show_atomic_number: bool = True,
) -> panflute.Math:
    return md.math(element_string(el_name, atomic_number, iso, show_atomic_number))

def isotope(el_name: str, iso: int) -> panflute.Math:
    return element(el_name, iso = iso)

from io import StringIO
import re

# ([A-Z][a-z]?)([0-9]+)?(\^[0-9]*[\+|\-])?

el_regex = re.compile(
    r"(?P<el>[A-Z][a-z]?)(?P<num>[0-9]+)?(?P<charge>\^[0-9]*[\+|\-])?"
)


def molecule(mol_string: str) -> str:
    out = StringIO()
    for el_match in el_regex.finditer(mol_string):
        el = el_match.group("el")
        num = el_match.group("num")
        charge = el_match.group("charge")
        out.write(f"\\text{{{el}}}")
        if num is not None:
            out.write(f"_{{\\text{{{num}}}}}")
        if charge is not None:
            charge = charge.lstrip("^")
            if charge[-1] not in ["+", "-"]:
                charge = charge + "+"
            out.write(f"^{{\\text{{{charge[:-1]}}}{charge[-1]}}}")
    return "$" + out.getvalue() + "$"


import re


def nuclear_reaction_string(input: str) -> str:
    replacements = []
    for match in re.finditer(
        r"(?P<A>\d+)?(\_(?P<Z>\d+))?(?P<el>[A-Znp][a-z]?)?(?P<extras>\\[^\s]+(\{.*?\})?)?",
        input,
    ):
        if len(match.group()) == 0:
            continue
        A = match.group("A")
        Z = match.group("Z")
        el = match.group("el")
        extras = match.group("extras")
        if el is not None:
            if el not in ["n", "p"]:
                out = element_string(el, atomic_number=Z, iso=A)
            else:
                if el == "n":
                    out = format_element("n", 1, 0)
                elif el == "p":
                    out = format_element("p", 1, 1)
                else:
                    out = format_element(el, A, Z)
            if extras is not None:
                out += " " + extras
        else:
            if el is None and extras is None:
                # this is just a number, so do nothing
                continue
            out = format_element((el if el is not None else "") + extras, A, Z)
            if A is None and Z is None:
                out = ""
                if el is not None:
                    out += f"\\text{{{el}}}"
                out += extras
        replacements.append((match.start(), match.end(), out))

    out = input
    for start, end, replacement in replacements[::-1]:
        out = out[:start] + replacement + out[end:]
    out = out.replace("->", "\ \\longrightarrow\ ")
    return out

def nuclear_reaction(input: str) -> str:
    return md.equation(nuclear_reaction_string(input))