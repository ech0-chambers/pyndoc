"""Configuration options and context managers for LaTeX rendering."""

import contextlib
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any


@dataclass
class LatexConfig:
    """Configuration options for LaTeX rendering and formatting."""

    default_format: str = ".4g"
    multiplication_operator: str = "\\times"
    auto_truncate_length: int = 6
    use_siunitx: bool = False
    use_exp_for_exponential: bool = False
    use_arc_for_inverse_trig: bool = False
    array_index_separate: bool = False
    array_index_bracket_type: str = "square"
    use_degrees: bool = False


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
]

