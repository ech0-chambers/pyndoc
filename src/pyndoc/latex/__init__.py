"""Pyndoc LaTeX rendering package: AST generation, units, formatting, and calculus."""

from typing import Any

from .calculus import *
from .calculus import __all__ as _calculus_all
from .config import *
from .config import __all__ as _config_all
from .containers import *
from .containers import __all__ as _containers_all
from .core import *
from .core import __all__ as _core_all
from .dsl import *
from .dsl import __all__ as _dsl_all
from .dsl import symbols as dsl_symbols
from .functions import *
from .functions import __all__ as _functions_all
from .quantity import *
from .quantity import __all__ as _quantity_all
from .symbols import *
from .symbols import __all__ as _symbols_all
from .typography import *
from .typography import __all__ as _typography_all
from .units import *
from .units import __all__ as _units_all

# Re-export symbols function from dsl so it is not shadowed by the submodule of the same name
symbols = dsl_symbols

# Target format state for Pandoc filter execution
TARGET_FORMAT: Any = None

__all__ = [
    "TARGET_FORMAT",
    *_config_all,
    *_core_all,
    *_units_all,
    *_quantity_all,
    *_typography_all,
    *_containers_all,
    *_functions_all,
    *_calculus_all,
    *_symbols_all,
    *_dsl_all,
]
