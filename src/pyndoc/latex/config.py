"""Configuration options and context managers for LaTeX rendering."""

import contextlib
from collections.abc import Generator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MultiplicationOperator(StrEnum):
    """Supported multiplication operators for LaTeX rendering."""

    TIMES = r"\times"
    CDOT = r"\cdot"

    @classmethod
    def _missing_(cls, value: object) -> "MultiplicationOperator":
        if isinstance(value, str):
            norm = value.strip().lower()
            if norm in ("times", r"\times"):
                return cls.TIMES
            if norm in ("cdot", r"\cdot"):
                return cls.CDOT
        raise ValueError(
            f"Invalid multiplication_operator '{value}': expected one of {[m.value for m in cls]} (or 'times', 'cdot')."
        )


class BracketType(StrEnum):
    """Supported bracket types for grouping and indexing in LaTeX."""

    SQUARE = "square"
    ROUND = "round"
    CURLY = "curly"
    ANGLE = "angle"
    ABSOLUTE = "absolute"

    @property
    def delimiters(self) -> tuple[str, str]:
        """Return the (left, right) LaTeX delimiters for this bracket type."""
        match self:
            case BracketType.SQUARE:
                return ("[", "]")
            case BracketType.ROUND:
                return ("(", ")")
            case BracketType.CURLY:
                return (r"\{", r"\}")
            case BracketType.ANGLE:
                return (r"\langle", r"\rangle")
            case BracketType.ABSOLUTE:
                return ("|", "|")

    @classmethod
    def _missing_(cls, value: object) -> "BracketType":
        if isinstance(value, str):
            norm = value.strip().lower()
            if norm in ("square", "[", "]", "brackets"):
                return cls.SQUARE
            if norm in ("round", "paren", "parenthesis", "parentheses", "(", ")"):
                return cls.ROUND
            if norm in ("curly", "brace", "braces", "{", "}", r"\{", r"\}"):
                return cls.CURLY
            if norm in ("angle", "<", ">", r"\langle", r"\rangle"):
                return cls.ANGLE
            if norm in ("absolute", "abs", "|"):
                return cls.ABSOLUTE
        raise ValueError(
            f"Invalid bracket_type '{value}': expected one of {[m.value for m in cls]}."
        )


@dataclass
class LatexConfig:
    """Configuration options for LaTeX rendering and formatting."""

    default_format: str = ".4g"
    multiplication_operator: MultiplicationOperator = MultiplicationOperator.TIMES
    auto_truncate_length: int = 6
    use_siunitx: bool = False
    use_exp_for_exponential: bool = False
    use_arc_for_inverse_trig: bool = False
    array_index_separate: bool = False
    array_index_bracket_type: BracketType = BracketType.SQUARE
    use_degrees: bool = False

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "multiplication_operator":
            value = MultiplicationOperator(value)
        elif name == "array_index_bracket_type":
            value = BracketType(value)
        super().__setattr__(name, value)


ACTIVE_CONFIG = LatexConfig()


@contextlib.contextmanager
def latex_config(**overrides: Any) -> Generator[LatexConfig, None, None]:
    """Context manager for temporary LaTeX formatting overrides.

    Parameters
    ----------
    **overrides : Any
        Key-value pairs corresponding to attributes of LatexConfig.

    Yields
    ------
    LatexConfig
        The active configuration object with overrides applied.
    """
    global ACTIVE_CONFIG
    for k in overrides:
        if not hasattr(ACTIVE_CONFIG, k):
            raise AttributeError(f"Invalid LatexConfig option: '{k}'")

    old_values = {k: getattr(ACTIVE_CONFIG, k) for k in overrides}
    for k, v in overrides.items():
        setattr(ACTIVE_CONFIG, k, v)
    try:
        yield ACTIVE_CONFIG
    finally:
        for k, v in old_values.items():
            setattr(ACTIVE_CONFIG, k, v)


__all__ = [
    "LatexConfig",
    "latex_config",
    "ACTIVE_CONFIG",
    "MultiplicationOperator",
    "BracketType",
]

