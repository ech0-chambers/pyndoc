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

For lengths %%(a == a()) and %%(b == b()), the hypotenuse is:

%%tex.split(
    [
        [c, c.expand],
        [c.expand()],
        [c()]
    ]
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

```python {.quiet}
q = tex.Quantity(9.80665, fmt=".2f", unit="m / s^2")
```

Calling a `Quantity` evaluates and formats its value for typesetting:

- `%%q()`{.example}
- `%%q(fmt=".4f")`{.example}
- `%%q(unit="ft / s^2")`{.example}

### `Variable` (`var`)

A `Variable` combines a symbol representation with an underlying `Quantity`:

```python {.quiet}
hbar = tex.var(r"\hbar", 1.0545718e-34, fmt=".3e", unit="kg m^2 / s")
```

This can be used in equations or text as a symbol or its value.

- When used directly in expressions, it renders its symbol: `%%hbar`{.example}.
- When called, it formats and renders its evaluated numeric quantity: `%%hbar()`{.example}.


### Multi-variable Declarations (`symbols`)

The `symbols()` function parses compact variable declarations separated by semicolons or newlines:

```python {.quiet}
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

## Expression Expansion

When defining variables from formulas, such as `t = tex.var("t", tex.sqrt(2 * h / g))`, Pyndoc retains the defining expression AST. You can expand the variable during typesetting without duplicating the formula:

| Syntax | Description | Example ($c = b^2 + 10$ where $b = 2a$) |
| :--- | :--- | :--- |
| `v.expand` | Single-layer symbolic expansion | $b^2 + 10$ |
| `v.expand()` | Single-layer evaluated expansion (substituting child variable values) | $6^2 + 10$ |
| `v.expand_to(depth)` | Expand expression up to `depth` levels (returns a callable token) | $c.\text{expand\_to}(2) \to (2a)^2 + 10$ |
| `v.expand_all` | Multi-layer recursive symbolic expansion down to atomic variables | $(2a)^2 + 10$ |
| `v.expand_all()` | Multi-layer recursive evaluated expansion down to atomic variable values | $(2 \times 3)^2 + 10$ |
| `v()` | Final evaluated quantity | $46$ |

### Complete Derivation Chains

Combining `.expand`, `.expand()`, and `()` with chained equalities produces complete mathematical derivations with zero copy-pasting:

```{.example title="Derivation Chaining"}
%{
    g = tex.var("g", 9.80665, fmt=".2f", unit="m / s^2")
    h = tex.var("h", 45.0, fmt=".1f", unit="m")
    t = tex.var("t", tex.sqrt(2 * h / g))
};

%%tex.split(
    [
        [t, t.expand],
        [t.expand()], 
        [t()]
    ]
)
```

### Selective Expansion (`expandable` and `no_expand`)

You can control whether intermediate variables are expanded in two ways:

1. **The `expandable` Flag**:
    When declaring a variable, set `expandable=False` (default is `True`) to treat it as atomic during all expansions:
    ```python {.quiet}
    a = tex.var("a", 3)
    b = tex.var("b", 2 * a)
    c = tex.var("c", b**2 + 10)
    ```
    By default, expressions will be expanded until they can't be expanded any further: `%%(c == c.expand_all)`{.example}, and with evaluation, `%%(c == c.expand_all())`{.example}. This can be disabled at any point:

    ```python {.quiet}
    b.expandable = False
    ```
    Now, expansion stops at `b`, leaving `b` symbolic: `%%(c == c.expand_all)`{.example}, and with evaluation, `%%(c == c.expand_all())`{.example}.

    You can also toggle `b.expandable = True` or `False` dynamically at any time, or pass it as a keyword argument to `tex.var`.

2. **The `no_expand` Parameter on `expand_to`**:
    Supply a list of variables (or a single variable) to `.expand_to(depth, no_expand=[...])`. Any matching variable will not be expanded, regardless of its `.expandable` setting:
    ```markdown {.example}
    %{
        b.expandable = True
    }
    Passing `depth = None` triggers full expansion, equivalent to `expand_all`: %%(c == c.expand_to(None, no_expand = [b])). This also works with evaluation: %%(c == c.expand_to(None, no_expand = [b])()).
    ```

### Formatting Overrides

You can temporarily override format specifiers during evaluation by passing `fmt`:

```python
# Formats all substituted values in the expansion to 3 decimal places
expr = t.expand(fmt=".3f")
```

### Multiplication Display

When an expression is evaluated with concrete numerical operands (such as `2 * h()`), Pyndoc automatically formats the multiplication with the configured operator ($2 \times 45.0\ \mathrm{m}$) rather than juxtaposition ($2\ 45.0\ \mathrm{m}$). You can choose between `\times` and `\cdot` globally or temporarily via `latex_config(multiplication_operator=tex.MultiplicationOperator.CDOT)` (or using string shorthand `"cdot"`).

## Configuration

Default formatting and typesetting options can be configured globally or temporarily via `latex_config()`. Supported options include `MultiplicationOperator` and `BracketType` enums (with friendly string coercion):

```python
with tex.latex_config(
    multiplication_operator=tex.MultiplicationOperator.CDOT,
    array_index_bracket_type=tex.BracketType.SQUARE,
    default_format=".3f",
):
    expr = tex.sym("x") @ tex.sym("y")  # Renders using \cdot instead of \times
```

Available `BracketType` options:
- `BracketType.SQUARE` (`"square"`, `[` `]`)
- `BracketType.ROUND` (`"round"`, `(` `)`)
- `BracketType.CURLY` (`"curly"`, `\{` `\}`)
- `BracketType.ANGLE` (`"angle"`, `\langle` `\rangle`)
- `BracketType.ABSOLUTE` (`"absolute"`, `|` `|`)

## Key Quirks to Note

1. **Chained Equalities**: Python optimizes chained comparisons like `a == b == c` by evaluating `(a == b) and (b == c)`. To produce a chained equation like $a = b = c$, group one comparison explicitly: `(a == b) == c` or `a == (b == c)`.
2. **Left-Hand Non-Tokens**: In expressions like `4 == x`, Python evaluates the integer's comparison method first. Ensure the left-hand operand is a `Token` (e.g. `tex.sym(4) == x` or `x == 4`) to maintain desired operand order.
