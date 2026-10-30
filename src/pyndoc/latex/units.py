"""Unit registry, parsing, and formatting with Pint integration."""

import re
from typing import Optional, Tuple
import pint
from .config import ACTIVE_CONFIG
from .core import as_token, Literal, set_unit_parser


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


@pint.register_unit_format("U")
def format_unit_simple(unit, registry, **options):
    out = []
    units = [(u, p) for u, p in unit.items()]
    units = sorted(units, key=lambda x: x[1], reverse=True)
    for u, p in units:
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
    r"""Parses a unit string into a pint.Unit object.
    The unit string may be in siunitx syntax (`\meter\per\second\squared`),
    written fully (`meter per second squared`), or abbreviated (`m/s^2` or `m s^-2`).
    """
    if isinstance(unit, pint.Unit):
        return unit
    if not isinstance(unit, str):
        raise TypeError(f"Expected pint.Unit or str, got {type(unit)}")
    if "\\" in unit:
        for prefix in __unit_prefixes:
            unit = re.sub(rf"\\{prefix}\s*\\", prefix, unit)
        unit = unit.replace("\\", " ")
        if unit.startswith("per "):
            unit = unit[4:]
            return 1 / ureg.parse_units(unit)
        return ureg.parse_units(unit)
    return ureg.parse_units(unit)


set_unit_parser(parse_unit)


def __truncate_zeros(value: str) -> str:
    if "." in value:
        integer, decimal = value.split(".")
        if (
            ACTIVE_CONFIG.auto_truncate_length >= 0
            and len(decimal) > ACTIVE_CONFIG.auto_truncate_length
        ):
            decimal = int(decimal[: ACTIVE_CONFIG.auto_truncate_length + 1])
            decimal = round(decimal, -1)
            if len(str(decimal)) > ACTIVE_CONFIG.auto_truncate_length:
                integer = str(int(integer) + 1)
                decimal = ""
        decimal = decimal.rstrip("0")
        if decimal:
            return f"{integer}.{decimal}"
        return integer
    return value


def format_unit(unit: pint.Unit, si: bool = False) -> str:
    r"""Formats a pint.Unit object.

    Parameters
    ----------
    unit : pint.Unit
        The unit to be formatted.
    si : bool, optional
        If True, the unit will be formatted using siunitx syntax.
        Otherwise, the unit will be formatted directly using `\mathrm`. Default False
    """
    if si:
        return f"{unit:Lx}"
    return f"{unit:U}"


def format_value(
    value: float | pint.Quantity,
    fmt: Optional[str] = None,
    unit: Optional[pint.Unit | str] = None,
) -> Tuple[str, bool]:
    r"""Formats a value with an optional unit."""
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
        fmt = ACTIVE_CONFIG.default_format
    if fmt is not None:
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
            + (f"\\ {format_unit(unit, si=ACTIVE_CONFIG.use_siunitx)}" if unit else ""),
            True,
        )
    if unit is None or unit.dimensionless and unit != ureg.percent:
        return print_value, False
    return (
        print_value + (f"\\ {format_unit(unit, si=ACTIVE_CONFIG.use_siunitx)}" if unit else ""),
        True,
    )


def unit(unit: str | pint.Unit, in_math_mode: bool = False) -> str:
    r"""Formats a unit."""
    if in_math_mode:
        return format_unit(parse_unit(unit))
    return "$" + format_unit(parse_unit(unit)) + "$"


def si(
    value: float | pint.Quantity | str,
    fmt: Optional[str] = None,
    unit: Optional[pint.Unit | str] = None,
    in_math_mode: bool = False,
    in_unit: Optional[pint.Unit | str] = None,
) -> Any:
    r"""Formats a value with SI units."""
    parse_value = True
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            parse_value = False
    if in_unit is not None:
        if unit is None and not isinstance(value, pint.Quantity):
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
        return as_token(value) * Literal("\\ ") * as_token(format_unit(parse_unit(unit)))
    if parse_value:
        return "$" + "\\ " + format_value(value, fmt, unit)[0] + "$"
    if unit is None:
        return "$" + value + "$"
    return "$" + value + "\\ " + format_unit(parse_unit(unit)) + "$"


__all__ = [
    "ureg",
    "parse_unit",
    "format_unit_simple",
    "format_unit",
    "format_value",
    "si",
    "unit",
]

