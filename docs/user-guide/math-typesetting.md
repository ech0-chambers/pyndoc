# Mathematical Typesetting

Pyndoc provides an abstract syntax tree (AST) generator for LaTeX mathematics through the `pyndoc.latex` submodule (aliased as `tex` in filter execution). It enables dynamic mathematical typesetting with automatic operator grouping, equation evaluation, and physical unit conversions.

## Overview

In standard Markdown, mathematics inside `$ ... $` or `$$ ... $$` is treated by Pandoc as raw, unparsed text. Consequently, embedding code blocks directly inside math delimiters (such as `` $a = `print(x)`{.py}$ ``) is invalid and unsupported by Pandoc.

Pyndoc circumvents this limitation by providing a Python-based AST where expressions are written with natural Python syntax and operators, then compiled to LaTeX and injected as native Pandoc math AST elements using `.py-md` or `%%`:

```markdown {.example title="Pythagorean Theorem"}
%{
a, b = tex.symbols("a = 3 cm; b = 4 cm")
c = tex.var("c", tex.sqrt(a**2 + b**2), fmt=".0f", unit="cm")
};

For legs %%(a == a()) and %%(b == b()), the hypotenuse is:

%%md.equation(
    (c == tex.sqrt(a()**2 + b()**2)) == c()
)
```

## Tokens & Operator Overloading

Math expressions in Pyndoc are built from the `Token` AST node hierarchy. By overloading Python operators, expressions compose naturally into LaTeX structures:

| Operator | Python Example | LaTeX Output | Rendered | Description |
| :--- | :---: | :--- | :---: | :--- |
| `(...)` | `(a + 2)` | `{a + 2}` | $a + 2$ | Natural evaluation precedence and grouping. |
| `(...,)` | `(a / b,)` | `\left(\frac{a}{b}\right)` | $\left(\frac{a}{b}\right)$ | Single-element tuple produces scalable parentheses. |
| `[...]` | `[a / b]` | `\left[\frac{a}{b}\right]` | $\left[\frac{a}{b}\right]$ | Single-element list produces scalable square brackets. |
| `{...}` | `{a / b}` | `\left\lbrace\frac{a}{b}\right\rbrace` | $\left\lbrace\frac{a}{b}\right\rbrace$ | Single-element set produces scalable curly braces. |
| `a[b]` | `a[b]` | `{a}_{b}` | $a_b$ | Subscript indexing. |
| `**` | `a**2` | `{a}^{2}` | $a^2$ | Superscript exponentiation. |
| `+`, `-` (unary) | `-a` | `-{a}` | $-a$ | Unary sign operators. |
| `*` | `a * b` | `a b` | $ab$ | Standard multiplication (implicit juxtaposition). |
| `@` | `a @ b` | `a \times b` | $a \times b$ | Matrix multiplication operator used for explicit multiplication signs. |
| `/` | `a / b` | `\frac{a}{b}` | $\frac{a}{b}$ | Standard fraction division. |
| `//` | `a // b` | `\dfrac{a}{b}` | $\dfrac{a}{b}$ | Display-mode fraction division (`\dfrac`). |
| `+`, `-` (binary) | `a + b` | `a + b` | $a + b$ | Binary addition and subtraction. |
| `&` | `a & b` | `a b` | $a\ b$ | Spaced token concatenation. |
| `==` | `a == b` | `a = b` | $a = b$ | Mathematical equality statement. |
| `<`, `<=` | `a < b`, `a <= b` | `a < b`, `a \leq b` | $a < b$, $a \le b$ | Inequalities. |
| `>`, `>=` | `a > b`, `a >= b` | `a > b`, `a \geq b` | $a > b$, $a \ge b$ | Inequalities. |
| `!=` | `a != b` | `a \neq b` | $a \ne b$ | Inequality statement. |

### Shorthand Inline Math

If an expression evaluated inside a `.py-md` directive (`%%...`) returns a `Token`, Pyndoc automatically wraps it in an inline math element. For example, `%%(a == b)` is equivalent to `%%md.math(a == b)`.

## Variables & Physical Quantities

Pyndoc provides three primary token classes:

### `Literal` (`sym`)

A `Literal` represents a static symbol or mathematical literal that participates in equations without evaluating numerically:

```python
x = tex.sym("x")
alpha = tex.sym(r"\alpha")
```

### `Quantity`

A `Quantity` pairs a numeric scalar with an optional unit (via Pint) and format specifier:

```python
q = tex.Quantity(9.80665, fmt=".2f", unit="m / s^2")
```

Calling a `Quantity` evaluates and formats its value for typesetting:
- `q()` $\to$ `9.81\ \mathrm{m}\:\mathrm{s}^{-2}`
- `q(fmt=".4f")` $\to$ `9.8067\ \mathrm{m}\:\mathrm{s}^{-2}`
- `q(unit="ft / s^2")` $\to$ `32.17\ \mathrm{ft}\:\mathrm{s}^{-2}`

### `Variable` (`var`)

A `Variable` combines a symbol representation with an underlying `Quantity`:

```python
hbar = tex.var(r"\hbar", 1.0545718e-34, fmt=".3e", unit="kg m^2 / s")
```

- When used directly in expressions (`hbar`), it renders its symbol: `\hbar` ($\hbar$).
- When called (`hbar()`), it formats and renders its evaluated numeric quantity: `$1.055 \times 10^{-34}\ \mathrm{kg}\:\mathrm{m}^2\:\mathrm{s}^{-1}$`.

### Multi-variable Declarations (`symbols`)

The `symbols()` function parses compact variable declarations separated by semicolons or newlines:

```python
tex.symbols("""
    a = 3 cm;
    b = 4 cm;
    c = 5.2 (.2f);
    v = 100 km / hour (.1f);
""", namespace=globals())
```

The general syntax is `<name> = <value> <unit> (<format>)`. Supplying `namespace=globals()` automatically injects the defined variables directly into your document namespace.

## Units & Pint Integration

Physical unit support is powered by `pint`. Units can be specified as standard strings or parsed unit instances:

```python
E = tex.Quantity(1.0, unit="eV")
# Convert unit when rendering:
print(E(unit="J"))
# Output: 1.602 \times 10^{-19} \mathrm{J}
```

Units propagate and convert automatically across arithmetic operations:

```python
width = tex.Quantity(2.0, unit="inch")
height = tex.Quantity(5.0, unit="cm")
area = width * height  # Resulting quantity has compatible area units
```

## Configuration

Default formatting and typesetting options can be configured globally or temporarily via `latex_config()`:

```python
with tex.latex_config(multiplication_operator=r"\cdot", default_format=".3f"):
    expr = tex.sym("x") @ tex.sym("y")  # Renders using \cdot instead of \times
```

## Key Quirks to Note

1. **Chained Equalities**: Python optimizes chained comparisons like `a == b == c` by evaluating `(a == b) and (b == c)`. To produce a chained equation like $a = b = c$, group one comparison explicitly: `(a == b) == c` or `a == (b == c)`.
2. **Left-Hand Non-Tokens**: In expressions like `4 == x`, Python evaluates the integer's comparison method first. Ensure the left-hand operand is a `Token` (e.g. `tex.sym(4) == x` or `x == 4`) to maintain desired operand order.
