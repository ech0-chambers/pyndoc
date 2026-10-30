"""Quantity and Variable representations with Pint integration."""

from typing import Optional, Any
import pint
from .core import (
    Token,
    CallableToken,
    Literal,
    DimensionedLiteral,
    register_token_converter,
)
from .units import ureg, parse_unit, format_value


class Quantity(CallableToken):
    def __init__(
        self,
        value: float | int | complex | pint.Quantity,
        fmt: Optional[str] = None,
        unit: Optional[pint.Unit | str] = None,
    ) -> None:
        r"""A quantity with a value and unit.

        Parameters
        ----------
        value : float | int | complex | pint.Quantity
            The value of the quantity.
        fmt : Optional[str], optional
            Format specifier. If None, default format will be used.
        unit : Optional[pint.Unit | str], optional
            The unit of the quantity.
        """
        if isinstance(value, Token):
            raise TypeError(
                f"Quantity expects a numeric scalar or pint.Quantity, not a Token ({type(value).__name__}). "
                "To create a Quantity from an expression or variable, use expr.as_quantity()."
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
                self._value = ureg.Quantity(self._initial_value, self._unit)
        elif isinstance(self._initial_value, pint.Quantity):
            self._initial_value = self._initial_value.to_preferred()
            self._unit = self._initial_value.units
            self._value = self._initial_value
        else:
            self._unit = None
            self._value = self._initial_value

    @property
    def value(self) -> Any:
        return self._value

    @property
    def unit(self) -> Optional[pint.Unit]:
        return self._unit

    @unit.setter
    def unit(self, unit: pint.Unit | str) -> None:
        if self._unit is None:
            self._unit = parse_unit(unit)
            self.value.unit = self._unit
            return
        try:
            self._value = self._value.to(parse_unit(unit))
            self._unit = self._value.units
        except pint.DimensionalityError:
            raise ValueError(f"Cannot convert {self._unit} to {unit}")

    @value.setter
    def value(self, value: float | pint.Quantity) -> None:
        if isinstance(value, pint.Quantity):
            self._unit = value.units
            self._value = value
            return
        self._initial_value = value
        if self._unit is not None:
            self._value = ureg.Quantity(value, self._unit)
        else:
            self._value = value

    @property
    def fmt(self) -> Optional[str]:
        return self._fmt

    @fmt.setter
    def fmt(self, fmt: Optional[str]) -> None:
        self._fmt = fmt

    def __call__(
        self, fmt: Optional[str] = None, unit: Optional[pint.Unit | str] = None
    ) -> Literal:
        r"""Returns a Token representing the quantity, formatted as specified."""
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


class Variable(CallableToken):
    def __init__(
        self,
        name: str,
        value: float | int | complex | pint.Quantity | Token,
        fmt: Optional[str] = None,
        unit: Optional[pint.Unit | str] = None,
    ) -> None:
        r"""A variable with a name, value, and optional unit and format specifier."""
        self.name = Literal(name)
        if isinstance(value, Token):
            value = value.value
        self._quantity = Quantity(value, fmt=fmt, unit=unit)

    def __str__(self) -> str:
        return str(self.name)

    def __call__(self, *args: Any, **kwargs: Any) -> Literal:
        return self._quantity(*args, **kwargs)

    @property
    def value(self) -> Any:
        return self._quantity.value

    @value.setter
    def value(self, val: Any) -> None:
        if isinstance(val, Token):
            val = val.value
        self._quantity.value = val

    @property
    def unit(self) -> Optional[pint.Unit]:
        return self._quantity.unit

    @unit.setter
    def unit(self, u: pint.Unit | str) -> None:
        self._quantity.unit = u

    @property
    def fmt(self) -> Optional[str]:
        return self._quantity.fmt

    @fmt.setter
    def fmt(self, f: Optional[str]) -> None:
        self._quantity.fmt = f

    def as_quantity(self) -> Quantity:
        return self._quantity


def var(
    name: str,
    value: float | int | complex | pint.Quantity | Token,
    fmt: Optional[str] = None,
    unit: Optional[pint.Unit | str] = None,
) -> Variable:
    r"""Create a variable with a name, value, and optional unit and format specifier."""
    return Variable(name, value, fmt, unit)


def _convert_quantity_like(v: Any) -> Quantity:
    if isinstance(v, pint.Quantity):
        return Quantity(v.magnitude, unit=v.units)
    if isinstance(v, int):
        return Quantity(v, fmt="d")
    return Quantity(v)


register_token_converter((int, float, complex, pint.Quantity), _convert_quantity_like)


__all__ = [
    "Quantity",
    "Variable",
    "var",
]

