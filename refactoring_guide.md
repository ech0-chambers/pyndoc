# Pyndoc Refactoring & Engineering Guide: From Prototype to Portfolio Showcase

This guide provides a comprehensive roadmap for testing, modularizing, hardening, and elevating the **Pyndoc** codebase into a production-grade portfolio project for senior software engineering roles.

---

## 1. Pre-Modularization Hardening: Fixing Core Architectural Flaws in `latex.py`

Before splitting `src/pyndoc/latex.py` (~3,950 lines) across multiple files, several foundational flaws in its design must be addressed in place. Resolving them now prevents propagating architectural bugs and circular dependencies into the new package structure.

### 1.1 Automatic Precedence-Based Parenthesization (Fixing `(a + b) * c`) [COMPLETED]

#### The Problem
`_BinaryOperator` defines `self.precedence = 0`, and subclasses assign precedence levels (`Addition` = 1, `Multiplication` = 2, `Power` = 3). However, **this precedence value is never inspected in `__str__` anywhere in the codebase.**
```python
a, b, c = var("a", 1), var("b", 2), var("c", 3)
expr = (a + b) * c
print(expr)  # Output: a + b  c  (Mathematically WRONG: missing grouping brackets!)
```
Currently, Pyndoc forces users to manually insert `tex.bracket(a + b) * c`.

#### The Fix: Precedence Hierarchy & Formatting Rules
1. Define standardized precedence constants:
   | Operator Category | Precedence | Examples |
   | :--- | :---: | :--- |
   | **Comparison** | `0` | `=`, `<`, `>`, `<=`, `>=`, `\approx`, `\equiv` |
   | **Addition / Subtraction** | `10` | `+`, `-` |
   | **Multiplication / Division** | `20` | `*` (implicit `ab`), `@` (explicit `\times`), `/` (`\frac`) |
   | **Unary / Negation** | `30` | `-x`, `+x` |
   | **Power / Index** | `40` | `^`, `_` |
   | **Atomic / Enclosed** | `100` | `Literal`, `Variable`, `Quantity`, `Bracket` |

2. Implement `_format_operand(operand, is_right: bool)` in `_BinaryOperator`:
   * An operand requires parentheses if its precedence is strictly less than the parent operator:
     $$\text{operand.precedence} < \text{self.precedence}$$
   * For non-associative operations (e.g. Subtraction $a - (b - c)$), the right operand also requires parentheses if its precedence is *equal* to the parent operator:
     $$\text{is\_right and operand.precedence} \le \text{self.precedence}$$
   * Fractions (`Division` using `\frac{num}{den}`) visually group operands via braces `{...}{...}`, so their numerator and denominator do not require extra parentheses unless rendered inline.

```python
# Implementation pattern for _BinaryOperator
def _needs_brackets(self, operand: Token, is_right: bool = False) -> bool:
    op_prec = getattr(operand, "precedence", 100)
    if op_prec < self.precedence:
        return True
    if is_right and op_prec == self.precedence and not getattr(self, "is_associative", True):
        return True
    return False

def _format_operand(self, operand: Token, is_right: bool = False) -> str:
    if self._needs_brackets(operand, is_right):
        return f"\\left({operand}\\right)"
    return str(operand)

def __str__(self) -> str:
    left_str = self._format_operand(self.left, is_right=False)
    right_str = self._format_operand(self.right, is_right=True)
    if self.symbol:
        return f"{left_str} {self.symbol} {right_str}"
    return f"{left_str} {right_str}"
```

---

### 1.2 Decoupling the Base `Token` "God Object" (Breaking Circular Dependencies)

#### The Problem
`Token` currently has **60+ convenience methods** (`sin`, `cos`, `tan`, `integral`, `derivative`, `prime`, `abs`, `sqrt`, `cbrt`, etc.) hardcoded directly onto it.
```python
class Token(ABC):
    def sin(self): return Sine(self)
    def integral(self, ...): return Integral(self, ...)
    def derivative(self, ...): return Derivative(self, ...)
```
In a single file, Python resolves these because method execution is deferred until call time. However, when splitting into `core.py`, `calculus.py`, `functions.py`, and `operators/`, `core.py`'s `Token` cannot import from `calculus.py` without creating unresolvable circular import chains.

#### The Fix: Functional Math + Dynamic Extension Binding
1. **Mathematical Functions as Standalone Callables:** Primary mathematical access should follow standard Python and SymPy conventions:
   ```python
   from pyndoc.latex import sin, cos, integral, diff
   expr = sin(x) + integral(y, variable=x)
   ```
2. **Dynamic Method Binding for Backward Compatibility:** To preserve method chaining (`x.sin()`, `x.derivative(...)`) without circular imports, keep `Token` in `core.py` minimal (only core dunder operators `__add__`, `__sub__`, etc.). Attach convenience methods dynamically *after* all classes are defined (in `latex/__init__.py`):
   ```python
   # src/pyndoc/latex/__init__.py
   def _bind_token_methods() -> None:
       """Bind convenience methods to Token after all subclasses are loaded."""
       from .functions import Sine, Cosine, Tangent, NthRoot
       from .calculus import Integral, Derivative
       from .containers import AbsoluteValue

       Token.sin = lambda self: Sine(self)
       Token.cos = lambda self: Cosine(self)
       Token.tan = lambda self: Tangent(self)
       Token.sqrt = lambda self: NthRoot(self, 2)
       Token.abs = lambda self: AbsoluteValue(self)
       Token.integral = lambda self, *args, **kwargs: Integral(self, *args, **kwargs)
       Token.derivative = lambda self, *args, **kwargs: Derivative(self, *args, **kwargs)
   ```
This cleanly isolates `core.py` from downstream mathematical packages.

---

### 1.3 Eliminating the "Infinite Unwrapping" Hack & Decoupling Quantity [COMPLETED]

#### The Root Cause & Structural Resolution
The `while i < 100` hack in `Quantity.__init__` was not merely an unwrapping loop—it was symptom-level plaster over a deeper design conflation between AST tokens, value objects, and formatters:
1. **Inheritance decoupled**: `_UnaryOperator` previously subclassed `Quantity` purely for code-reuse (`as_quantity`, `__float__`, `__int__`). `_UnaryOperator` now inherits directly from `CallableToken`, and common conversion methods were promoted to `CallableToken`.
2. **Composition for `Variable`**: `Variable` now subclasses `CallableToken` and holds a private `Quantity` instance rather than inheriting its internals.
3. **Strict constructor contract for `Quantity`**: `Quantity.__init__` now accepts *only* pure numeric scalars (`int | float | complex`) or `pint.Quantity`. It strictly rejects `Token` instances with a descriptive `TypeError`.
4. **Zero-unpacking architecture**: Tokens convert to `Quantity` via `expr.as_quantity()`. No looping or nested unwrapping is required.
5. **Fixed `NthRoot` child storage**: Renamed `NthRoot.value` (which previously shadowed the computed root with the child AST node) to `self.expr`, and added a dynamic `.value` property.

---

### 1.4 Pure AST Construction (Removing Mutation in `Power.__init__`) [COMPLETED]

#### The Problem
`Power.__init__` currently mutates its own AST nodes at initialization time:
```python
if isinstance(self.left, DimensionedLiteral):
    self.left = Bracket(self.left, scale=True)
```
The inline comment acknowledges this flaw:
`# Should this be in the string conversion rather than here? Would mean changes to _BinaryOperator or a separate __str__ for Power.`
Mutating child nodes during `__init__` violates AST integrity and causes inconsistent behavior when the same node is shared across multiple expressions.

#### The Fix: Render-Time Formatting
Keep `self.left` unchanged during initialization. In `Power.__str__`, apply bracket formatting dynamically if the base is a `DimensionedLiteral` or has lower precedence:
```python
class Power(_BinaryOperator):
    def __init__(self, left: Token | str | float, right: Token | str | float) -> None:
        super().__init__(left, right)
        self.symbol = "^"
        self.precedence = 40

    def __str__(self) -> str:
        # If the base has units or lower precedence, wrap in grouping brackets
        if isinstance(self.left, DimensionedLiteral) or self._needs_brackets(self.left, is_right=False):
            base_str = f"\\left({self.left}\\right)"
        else:
            base_str = f"{{{self.left}}}" if getattr(self.left, "precedence", 100) < 100 else str(self.left)
            
        exp_str = f"{{{self.right}}}"
        return f"{base_str}^{exp_str}"
```

---

### 1.5 Encapsulating Global Settings with `LatexConfig` [COMPLETED]

#### The Problem
Module-level variables control LaTeX generation globally:
```python
DEFAULT_FORMAT = ".4g"
MULTIPLICATION_OPERATOR = "\\times"
USE_SIUNITX = False
USE_EXP_FOR_EXPONENTIAL = False
```
Modifying these variables creates concurrency issues across documents and prevents local formatting overrides within sub-sections.

#### The Fix: `LatexConfig` Dataclass & Context Manager
```python
from dataclasses import dataclass, field
import contextlib

@dataclass
class LatexConfig:
    default_format: str = ".4g"
    multiplication_operator: str = "\\times"
    auto_truncate_length: int = 6
    use_siunitx: bool = False
    use_exp_for_exponential: bool = False
    use_arc_for_inverse_trig: bool = False
    array_index_separate: bool = False
    array_index_bracket_type: str = "square"

# Active default configuration
ACTIVE_CONFIG = LatexConfig()

@contextlib.contextmanager
def latex_config(**overrides):
    """Context manager for temporary LaTeX formatting overrides."""
    global ACTIVE_CONFIG
    old_values = {k: getattr(ACTIVE_CONFIG, k) for k in overrides}
    for k, v in overrides.items():
        setattr(ACTIVE_CONFIG, k, v)
    try:
        yield ACTIVE_CONFIG
    finally:
        for k, v in old_values.items():
            setattr(ACTIVE_CONFIG, k, v)
```
Configuration is accessed and modified cleanly via `ACTIVE_CONFIG` or scoped locally via `latex_config(**overrides)`, eliminating module-level metaprogramming and alias dictionaries.

---

### 1.6 Eliminating Escape Sequence `SyntaxWarning`s [COMPLETED]

#### The Problem
Python 3.12+ issues compiler warnings for invalid escape sequences in string docstrings:
```text
SyntaxWarning: "\m" is an invalid escape sequence. Did you mean "\\m"?
```
This occurs across lines in `src/pyndoc/latex.py` and `docs/examples/atomic.py`.

#### The Fix: Raw String Docstrings
Convert all docstrings containing LaTeX backslashes (`\meter`, `\per`, `\LaTeX`, etc.) to raw string literals: `r"""..."""`. Verified with `-W error -m compileall -f` across all source and test files.

---

## 2. Architectural Decomposition: Modularizing `latex.py` into `pyndoc.latex`

Once the hardening steps above are implemented and verified in place, `latex.py` can be cleanly decomposed into the `src/pyndoc/latex/` package without circular dependency issues.

### Proposed Package Layout

```
src/pyndoc/latex/
├── __init__.py           # Public API re-exports & _bind_token_methods()
├── config.py             # LatexConfig dataclass & latex_config context manager
├── core.py               # Token, CallableToken, Literal, DimensionedLiteral, Argument, Macro, Environment
├── units.py              # Pint UnitRegistry configuration, parse_unit, format_unit, format_value, si, unit
├── quantity.py           # Quantity, Variable, unwrap_numeric_value
├── operators/
│   ├── __init__.py
│   ├── base.py           # _UnaryOperator, _BinaryOperator, _BooleanBinaryOperator
│   ├── arithmetic.py     # Addition, Subtraction, Multiplication, Times, Division, Power, Index
│   └── comparison.py     # Equality, LessThan, GreaterThan, LessThanOrEqual, GreaterThanOrEqual, Approximation
├── containers.py         # Bracket, SquareBracket, CurlyBracket, AngleBracket, AbsoluteValue, MixedBracket, ArrayIndex
├── calculus.py           # Integral, Derivative, PartialDerivative, Limit, Summation
├── functions.py          # NthRoot, Trig functions, Hyperbolic functions, Exponential, Logarithm
└── symbols.py            # __pythonify_name, define_symbols, symbols, DEFAULT_NAMESPACE
```

### Module Responsibilities

1. **`config.py`**:
   * Encapsulates `LatexConfig` and `latex_config` context manager.
2. **`core.py`**:
   * Base AST node definitions: `Token`, `CallableToken`, `Literal`, `DimensionedLiteral`.
   * TeX syntax elements: `Argument`, `Macro`, `Environment`.
   * Type coercion helpers: `as_token`, `sym`, `symbol`.
3. **`units.py`**:
   * Application-wide `pint.UnitRegistry` configuration and preferred base units.
   * Unit parsing (`parse_unit`) and formatting (`format_unit`, `format_value`, `si`, `unit`).
4. **`quantity.py`**:
   * `Quantity`: Numeric magnitudes with physical units, string formatting, and Pint arithmetic.
   * `Variable`: Symbolic naming for LaTeX equations with numerical value on call.
   * `unwrap_numeric_value`: Cycle-safe unwrapping of token values.
5. **`operators/`**:
   * `base.py`: Operator evaluation hooks and precedence-based parenthesization.
   * `arithmetic.py`: Overloaded operations (`+`, `-`, `*`, `@`, `/`, `^`, `_`).
   * `comparison.py`: Boolean comparisons (`=`, `<`, `>`, `<=`, `>=`, `\approx`, `\equiv`).
6. **`containers.py`**:
   * Grouping structures (`()`, `[]`, `{}`, `<>`, `||`) with `\left` and `\right` scaling.
   * Array indexing representation (`a[i, j]`).
7. **`calculus.py`**:
   * Integrals, derivatives, partial derivatives, limits, and summations.
8. **`functions.py`**:
   * Standalone mathematical callables and AST nodes (`sin`, `cos`, `tan`, `exp`, `log`, etc.).
9. **`symbols.py`**:
   * Shorthand DSL parser (`define_symbols`): Splits statement blocks, extracts variable names, initial values, unit strings, and format specifiers.

### Backward Compatibility Re-Exports (`latex/__init__.py`)

```python
# src/pyndoc/latex/__init__.py
from .config import LatexConfig, latex_config, ACTIVE_CONFIG
from .core import Token, Literal, DimensionedLiteral, Macro, Environment, as_token, sym, symbol
from .units import ureg, parse_unit, format_unit, format_value, si, unit
from .quantity import Quantity, Variable, unwrap_numeric_value
from .operators.arithmetic import (
    Addition, Subtraction, Multiplication, Times, Division, Power, Index
)
from .operators.comparison import (
    Equality, LessThan, GreaterThan, LessThanOrEqual, GreaterThanOrEqual,
    NotEqual, Approximation, Equivalence
)
from .containers import (
    Bracket, SquareBracket, CurlyBracket, AngleBracket, AbsoluteValue,
    MixedBracket, ArrayIndex
)
from .calculus import Integral, Derivative, PartialDerivative, Limit, Summation
from .functions import (
    NthRoot, Sine, Cosine, Tangent, Exponential, Logarithm,
    sin, cos, tan, sqrt, cbrt, exp, ln, log
)
from .symbols import symbols, define_symbols, DEFAULT_NAMESPACE

# Alias var -> Variable for backwards compatibility
var = Variable

# Backward compatible module-level configuration aliases
DEFAULT_FORMAT = ACTIVE_CONFIG.default_format
MULTIPLICATION_OPERATOR = ACTIVE_CONFIG.multiplication_operator
USE_SIUNITX = ACTIVE_CONFIG.use_siunitx

# Dynamically attach convenience methods to Token without circular imports
from . import _bind_token_methods
_bind_token_methods()

__all__ = [
    "Token", "Literal", "DimensionedLiteral", "Quantity", "Variable", "var",
    "symbols", "define_symbols", "DEFAULT_NAMESPACE", "si", "unit", "ureg", "as_token",
    "LatexConfig", "latex_config", "sin", "cos", "tan", "sqrt", "cbrt", "exp", "ln", "log"
]
```

---

## 3. In-Process Filter Architecture (Replacing Background Socket Server)

### Why the Background Server Was Retired

The prototype architecture used a background TCP server (`server.py`), client utility (`server_utils.py`), and working directory lockfile (`.pyndoc.json`). This was modeled after LuaLaTeX tools (like `pyluatex`), where Lua must repeatedly call Python snippets. 

However, **Pandoc filters run once per document conversion as a single, long-lived Python process.** Because Pandoc parses the whole document into an AST first and feeds it to the filter sequentially, a background socket server introduced severe drawbacks without any benefits:

1. **IPC Overhead & Double Serialization:** Every code block required opening a TCP socket, spawning a thread, serializing Panflute AST nodes to JSON, sending over loopback, deserializing, and reconstructing Panflute elements with a custom recursive walker (`element_from_json`).
2. **Concurrency Hazards:** Multiple concurrent builds (e.g. `make -j4`) collided on `.pyndoc.json` and static port allocations.
3. **Socket Boundary Fragility:** Fixed-size buffers (`recv(16384)`), port scanning retries, and potential orphaned daemon processes.

### Modern Architecture: Direct In-Process AST Transformation

In the modernized architecture, [`src/pyndoc/filter.py`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/filter.py) manages its own persistent execution environment directly in memory:

```text
Pandoc CLI / Pyndoc Runner
            │
            ▼
   pandoc --filter=pyndoc/filter.py [args]
            │
            ▼ (Single process lifecycle)
   panflute.run_filter(prepare=prepare, action=filter)
            │
            ├─► prepare(doc): Resolves target format, initializes clean USER_NAMESPACE
            │
            ├─► filter(elem):
            │     ├── .py     ──► exec(code, USER_NAMESPACE) + stdout capture
            │     ├── .py-md  ──► eval(code, USER_NAMESPACE) ──► Direct AST Injection
            │     └── .py-file──► exec(file, USER_NAMESPACE) + stdout capture
            │
            ▼
   Direct AST Replacement (Zero JSON IPC, Zero Sockets, Zero Lockfiles)
```

### Dedicated Document Namespace (`USER_NAMESPACE`)

Rather than polluting Python's `globals()`, document code executes inside a dedicated, isolated namespace:

```python
# src/pyndoc/filter.py
def create_user_namespace() -> dict[str, Any]:
    """Create a fresh execution namespace for document code evaluation."""
    ns: dict[str, Any] = {
        "__name__": "__main__",
        "__doc__": None,
        "__builtins__": __builtins__,
        "md": md,
        "tex": tex,
        "Format": Format,
        "panflute": panflute,
        "pf": panflute,
    }
    # Bind as default namespace for shorthand symbol declarations
    tex.DEFAULT_NAMESPACE = ns
    return ns
```

- **Seamless `tex.symbols` Integration:** `tex.symbols("m = 5 kg; C = 4180 J/kg/K;")` automatically writes directly into `USER_NAMESPACE` without requiring `globals()` as a second argument.
- **Direct AST Injection:** Expressions returning `panflute.Element` (e.g. `md.equation(...)` or `m()`) are placed straight into the document tree without JSON intermediate serialization.

---

## 4. Preprocessor Engine & Diagnostic Error Reporting

[`src/pyndoc/preprocess.py`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/preprocess.py) handles macro parsing, file inclusion (`%%%py`, `%%%md`, `%%%mdifformat`), and block extraction before handing the document off to Pandoc.

### Fast Regex-Jump Engine (`TRIGGER_RE`)

The preprocessor was migrated from an $O(N^2)$ chunk-slicing scanner to a compiled regex-jump engine (`TRIGGER_RE = re.compile(r"[%`~\$\\]|<!--")`). This benchmarks at a **315x speedup** on large documents (38 ms vs. 12.1 s).

### Horizontal Context Windowing

When syntax errors occur, terminals narrower than the line length soft-wrap, breaking naive caret underlines (`" " * col + "^" * len`). 

[`_format_windowed_line`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/preprocess.py#L98-L162) implements horizontal context windowing:
- Dynamically queries terminal width via `shutil.get_terminal_size()`.
- Crops long lines with ellipses (`...`) centered on the error token:
  ```text
  >   ...def calculate(alpha, beta, %(bad_macro + 1), gamma, delta)...
  >                                 ^~~~~~~~~~~
  ```
- Mathematically guarantees that error lines never soft-wrap, preserving 1:1 visual alignment under the error site across all terminals, IDE output panels, and log files.

### Module-Level Diagnostic Console

- `_CONSOLE: Console | None`: Configured lazily in `preprocess()`.
- [`no_console()`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/preprocess.py#L89): Directs Rich diagnostic output to an in-memory buffer (`io.StringIO`), suppressing terminal output for headless or test environments while retaining clean plain-ASCII exception messages.

---

## 5. Modernized Logging & Timer Infrastructure

All logging across [`src/pyndoc/__main__.py`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/__main__.py), [`src/pyndoc/filter.py`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/filter.py), and related modules follows current Python 3.11+ best practices:

1. **Eliminated `getLevelName()` Anti-pattern:** Uses [`logging.getLevelNamesMapping()`](https://docs.python.org/3/library/logging.html#logging.getLevelNamesMapping) for level validation, and passes string levels directly to `logging.basicConfig(level=level)`.
2. **Hierarchical Loggers:** Replaced root `logging.info/debug/warning` calls with module loggers (`logger = logging.getLogger("pyndoc")`, `pyndoc.filter`, etc.).
3. **Robust Handlers:** Configured with `filemode="w"`, `encoding="utf-8"` (safe for Unicode math symbols on all platforms), and `force=True`.
4. **Structured Task Execution Timing ([`src/pyndoc/timer.py`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/timer.py)):**
   * Replaced ad-hoc `time.perf_counter_ns()` measurements with a context manager (`Timer`).
   * Automatically formats elapsed time into adaptive units (`#ns`, `#ms`, `#s`, `#m #s`, `#h #m #s` with 1 d.p. for seconds and smaller).
   * Differentiates between task completion and task failure on exceptions.

---

## 6. Automated Testing Suite

Comprehensive unit and integration test coverage across all components:

### Test Directory Layout

```
tests/
├── conftest.py                   # sys.path configuration and shared fixtures
└── unit/
    ├── test_preprocess.py        # Macro expansion, delimiters, bracket matching, windowing
    ├── test_logging.py           # Logging levels, hierarchy, formatting, string buffer capture
    ├── test_filter.py            # In-process code execution, USER_NAMESPACE, AST transforms
    └── test_timer.py             # format_time_ns, Timer context manager, stdout/logger routing
```

### Verified Test Results

- **84 passing unit tests** executing in **0.22s**.
- **100% test coverage** on [`src/pyndoc/timer.py`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/timer.py).
- **86% test coverage** on [`src/pyndoc/preprocess.py`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/preprocess.py).
- End-to-end verification of [`docs/examples/math_example.md`](file:///home/echo/Documents/python_github/pyndoc/docs/examples/math_example.md) compiling directly to HTML through Pandoc with full equation rendering and unit propagation.

---

## 7. Shorthand DSL Hardening (`define_symbols` Without External Dependencies)

Rather than introducing an external parser generator library (such as Lark), the `define_symbols` DSL will be upgraded to production quality using Python's standard library. 

### Proposed Standard-Library Implementation

A documented, readable `re.VERBOSE` pattern adds support for quoted string literals (`"..."` / `'...'`), negative and scientific notation floats, physical units, format specifiers, and line comments:

```python
# Planned for src/pyndoc/latex/symbols.py
import re
from typing import Any, Dict, Optional, Tuple
from pyndoc.latex.core import Token, as_token
from pyndoc.latex.quantity import Variable

SYMBOL_STATEMENT_RE = re.compile(
    r"""
    ^\s*
    (?P<name>[a-zA-Z_][a-zA-Z0-9_]*)              # Identifier name
    (?:
        \s*=\s*
        (?:
            (?P<quote>["'])(?P<str_val>.*?)(?P=quote) # Quoted string literal
          | (?P<num_val>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) # Number (int/float/sci)
        )
        (?:\s+(?P<units>[^\(;]+?))?               # Optional physical unit string
        (?:\s*\((?P<fmt>[^\)]+)\))?               # Optional format specifier: (.3f)
    )?
    \s*;?\s*$
    """,
    re.VERBOSE,
)


def define_symbols(
    statements: str,
    namespace: Optional[Dict[str, Any]] = None,
) -> Tuple[Token, ...]:
    """Parse shorthand symbol declaration statements into Variable or Token objects."""
    if namespace is None:
        namespace = DEFAULT_NAMESPACE

    raw_lines = statements.splitlines()
    raw_statements = []
    for line in raw_lines:
        line_without_comment = line.split("#", 1)[0].strip()
        if not line_without_comment:
            continue
        for part in line_without_comment.split(";"):
            cleaned = part.strip()
            if cleaned:
                raw_statements.append(cleaned)

    assignments: list[Token] = []
    for stmt in raw_statements:
        match = SYMBOL_STATEMENT_RE.match(stmt)
        if not match:
            raise ValueError(f"Could not parse symbol declaration: '{stmt}'")

        name = match.group("name")
        str_val = match.group("str_val")
        num_val = match.group("num_val")
        units = match.group("units")
        fmt = match.group("fmt")

        if str_val is not None:
            symbol_obj = Variable(name, str_val, unit=units, fmt=fmt)
        elif num_val is not None:
            val: int | float = float(num_val)
            if val.is_integer():
                val = int(val)
            symbol_obj = Variable(name, val, unit=units, fmt=fmt)
        else:
            symbol_obj = as_token(name)

        if namespace is not None:
            namespace[name] = symbol_obj
        assignments.append(symbol_obj)

    return tuple(assignments)
```

---

## 8. Professional Packaging & CI Pipeline

### 1. Modern `pyproject.toml`
* Remove legacy `setup.py`.
* Ensure modern PEP 517/621 packaging:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pyndoc"
version = "0.2.0"
description = "Pandoc preprocessor and filter for Python execution at build time."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "AGPL-3.0-only" }
authors = [{ name = "Peter Brookes Chambers" }]
dependencies = [
    "panflute>=2.3.0",
    "pyyaml>=6.0",
    "pint>=0.23",
    "rich>=12.0.0",
    "numpy>=1.24.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.6.0"
]

[project.scripts]
pyndoc = "pyndoc.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 2. GitHub Actions CI (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [ main, master, refactor ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - name: Install Pandoc
        run: sudo apt-get install -y pandoc
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - name: Install Dependencies
        run: pip install .[dev]
      - name: Lint with Ruff
        run: ruff check src/ tests/
      - name: Run Test Suite
        run: pytest --cov=pyndoc --cov-report=term-missing tests/
```

---

## 9. Phased Implementation Status

| Phase | Objective | Status | Deliverables |
|---|---|---|---|
| **Phase 1** | Preprocessor & Diagnostics | **Completed** | Regex-jump parser (315x faster), horizontal windowing, Rich console capture, 55 unit tests (86% coverage). |
| **Phase 2** | In-Process Filter & Logging | **Completed** | Removed TCP socket server and `.pyndoc.json`. Added `USER_NAMESPACE`, `tex.DEFAULT_NAMESPACE`, modernized logging, and `Timer` context manager (84 passing tests). |
| **Phase 3A** | In-Place `latex.py` Hardening | **Next** | Fix operator precedence parenthesization, decouple `Token` circular dependencies, eliminate `i < 100` hack, fix docstring escape sequences, and add `LatexConfig`. |
| **Phase 3B** | Package Modularization | **Planned** | Decompose monolithic `src/pyndoc/latex.py` (~3,950 lines) into `src/pyndoc/latex/` package modules (`core`, `units`, `quantity`, `operators`, `calculus`, `symbols`). |
| **Phase 4** | Shorthand DSL Hardening | **Planned** | Polish `define_symbols` using zero-dependency `re.VERBOSE` pattern to support quoted string literals and scientific notation floats with clear error reporting. |
| **Phase 5** | Project Hygiene & CI | **Planned** | Remove legacy `server.py` and `server_utils.py`, update `pyproject.toml`, remove dead code, and configure GitHub Actions CI. |
