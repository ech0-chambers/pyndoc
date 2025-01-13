# Maths in Pyndoc

Standard markdown syntax for maths will work as expected. `$a = 4$` will render as $a=4$ and similarly for display mode maths. This is unaffected by the inclusion of the Pyndoc filter, with or without the preprocessor.

However, since Pandoc does not parse maths in the same way that it parses general text, it's not possible to include code blocks within maths environments. ``$a = `code`$`` is not standard markdown syntax, and so we cannot simply apply a `.py` class like `` $a = `print(a)`{.py}$``. This means that maths cannot be dynamically generated in the same way as other text.

This would be a serious limitation in many applications. To circumvent this, one would have to construct the appropriate Panflute `Math` element directly, which would be quite cumbersome. To make this easier, a module `latex.py` is available under the alias `tex` with a series of convenience functions and classes to make writing maths as natural as possible. This module is automatically imported into the filter, and so is available in any python code in the documents (though usually it would be passed directly to a call to the `md.math` function -- see the `markdown.py` [documentation](markdown.md))

For a practical example showing use of `Variable`s, formatting and printing, and units, see [math_example.md](examples/math_example.md?plain=1) and the corresponding [math_example.pdf](examples/math_example.pdf).

## Using `sympy` as an Alternative

If you are already familiar with the `sympy` python module, you may find it easier to simply use this to generate the expressions you need, then convert them to LaTeX with the `sympy.latex` printer before passing this to the `md.math` function (or `md.equation` for display maths). For example, to construct the equation $x^3 + 2 = 11$, you could write (using the preprocessor syntax)
```markdown
%{import sympy}

%%md.equation(
    sympy.latex(sympy.Eq(sympy.Symbol("x")**3 + 2, 11))
)
```

Of course, importing Sympy adds some (albeit small) overhead to converting the document if it isn't used for any of its other capabilities. The equivalent using the `tex` module would be
```markdown
%%md.equation(
    tex.sym("x") ** 3 + 2 == 11
)
```

Both produce

> $$x^{3} + 2 = 11$$

## Operators

Maths in Pyndoc is built around the abstract `Token` class, which allows us to take advantage of Python's operator overloading. These will mostly be used through the `tex.sym` function, the `tex.var` function, or the `tex.Quantity` class. These are detailed in [](). For binary operators (`+`, `==`, `/` etc), if either the left or right operand is a `Token`, the result will be a `Token` which constructs the appropriate LaTeX. All operators which are handled by the `Token` class are listed below, in order of precedence (from highest to lowest).

| Operator                     | Example      | Method Equivalent | LaTeX                                  | Rendered                                | Description                                                                                                                                                                                                                                                                      |
|------------------------------|:------------:|:-----------------:|----------------------------------------|:---------------------------------------:|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `(...)`                      | `(a + 2)`    | `a.add(2)`        | `{a+2}`                                | $a+2$                                   | Used just like in normal Python to control the order of evaluation                                                                                                                                                                                                               |
| `(… , )` (Tuple constructor) | `(a/b,)`     |                   | `\left(\frac{a}{b}\right)`             | $\left(\dfrac{a}{b}\right)$             | A tuple with a single element is encased in (scalable) parentheses. Note that a tuple is constructed by the comma, not just by the parentheses.                                                                                                                                  |
| `[...]` (List constructor)   | `[a/b]`      |                   | `\left[\frac{a}{b}\right]`             | $\left[\dfrac{a}{b}\right]$             | A list with a single element is encased in (scalable) square brackets                                                                                                                                                                                                            |
| `{...}` (Set constructor)    | `{a/b}`      |                   | `\left\lbrace\frac{a}{b}\right\rbrace` | $\left\lbrace\dfrac{a}{b}\right\rbrace$ | A set with a single element is encased in (scalable) braces                                                                                                                                                                                                                      |
| `...[...]`                   | `a[b]`       | `a.index(b)`      | `{a}_{b}`                              | $a_b$                                   | An index will be treated as a subscript (assuming `a` is an `Expression` object)                                                                                                                                                                                                 |
| `**`                         | `a**2`       | `a.power(b)`      | `{a}^{2}`                              | $a^2$                                   | The exponentiation operator results in an exponent (superscript)                                                                                                                                                                                                                 |
| `+` (unary)                  | `+a`         |                   | `+{a}`                                 | $+a$                                    | Unary plus and minus have the expected result.                                                                                                                                                                                                                                   |
| `-` (unary)                  | `-a`         |                   | `-{a}`                                 | $-a$                                    |                                                                                                                                                                                                                                                                                  |
| `*`                          | `a*b`        | `a.multiply(b)`   | `a b`                                  | $ab$                                    | The standard multiplication operator is rendered as implicit multiplication                                                                                                                                                                                                      |
| `@`                          | `a@b`        | `a.times(b)`      | `a \times b`                           | $a \times b$                            | The matrix multiplication operator can be used when implicit multiplication would be ambiguous, and inserts a multiplication symbol ($\times$) between the expressions                                                                                                           |
| `/`                          | `a/b`        | `a.divide(b)`     | `\frac{a}{b}`                          | $\frac{a}{b}$                           | True division results in a fraction                                                                                                                                                                                                                                              |
| `//`                         | `a//b`       |                   | `\dfrac{a}{b}`                         | $\dfrac{a}{b}$                          | Floor division forces a display-mode fraction, regardless of the math environment (using `\dfrac`)                                                                                                                                                                               |
| `+` (binary)                 | `a+b`        | `a.plus(b)`       | `a+b`                                  | $a+b$                                   | Binary addition and subtraction have the expected result in the typeset equation. Note that this overrides the use of `+` for string concatenation if one of the operands is an Expression.                                                                                      |
| `-` (binary)                 | `a-b`        | `a.minus(b)`      | `a-b`                                  | $a-b$                                   |                                                                                                                                                                                                                                                                                  |
| `&`                          | `a & “text”` |                   | `a text`                               | $a text$                                | Since `+` is used for the addition operator, a bitwise AND has been repurposed for string concatenation. The `Expression` is converted to a string, then concatenated with the `str` as normal. Note that the result of this is another `str`, **not** an `Token` object.        |
| `==`                         | `a == b`     | `a.equals(b)`     | `a = b`                                | $a = b$                                 | Conditional tests in the Python code are statements in the LaTeX output.                                                                                                                                                                                                         |
| `<`                          | `a<b`        | `a.lt(b)`         | `a < b`                                | $a < b$                                 |                                                                                                                                                                                                                                                                                  |
| `<=`                         | `a<=b`       | `a.leq(b)`        | `a \leq b`                             | $a\leq b$                               |                                                                                                                                                                                                                                                                                  |
| `>`                          | `a>b`        | `a.gt(b)`         | `a > b`                                | $a > b$                                 |                                                                                                                                                                                                                                                                                  |
| `>=`                         | `a>=b`       | `a.gew(b)`        | `a \geq b`                             | $a\geq b$                               |                                                                                                                                                                                                                                                                                  |
| `!=`                         | `a!=b`       | `a.new(b)`        | `a \neq b`                             | $a\neq b$                               |                                                                                                                                                                                                                                                                                  |

### Shorthand for Inline Maths

Constantly writing `%%md.math(...)` quickly becomes tedious, and so if Pyndoc is expecting a Panflute element but instead recieves a `Token`, the `Token` will automatically be placed inside a math environment. For example, `%%md.math(a)` and `%%a` are equivalent, as is `%%md.math(a == b)` and `%%(a == b)`. This also applies to called tokens, including more complicated expressions, for example:
```markdown
%{
    a, b = tex.symbols("a = 3 cm; b = 4 cm")
}

A right angle triangle with side lengths %%a() and %%b() has a hypotenuse with length %%tex.sqrt(a ** 2 + b ** 2)().
```

> A right angle triangle with side lengths $3\ \mathrm{cm}$ and $4\ \mathrm{cm}$ has a hypotenuse with length $5\ \mathrm{cm}$.

## Instantiating `Token`s

Most objects used in the `tex` module will be one of three classes:

- A `Literal` instance contains a string or float value. It obeys the operators defined above, but cannot be called. This should generally be used for variables which have no numeric value, or for a number which needs to be typeset alongside other expressions. These can be created with the function `tex.sym(value: str | float | Any) -> Literal`.
- A `Quantity` instance contains a numeric value and optionally a format specifier and unit. `Quantity` objects should always be called when they are used in an expression (see [Printing Values](#printing-values)) -- not doing so can result in unexpected behaviour regarding grouping. The `value` of a `Quantity` can be another expression, in which case the units will be inferred (or converted if the `unit` argument is also provided). These can be instantiated directly with `tex.Quantity(value: float | Token, fmt: Optional[str] = None, unit: Optional[pint.Unit | str] = None) -> Quantity`.
- A `Variable` combines the functionality from both `tex.sym` and `tex.Quantity`, storing a variable name as well as a value, format specifier, and unit. This should be used for variables which will be printed as their name and their value, such as 

  ```markdown
  %{
      hbar = tex.var("\\hbar", 1.0545718e-34, unit = "kg m^2 / s")
  }
  
  The reduced Planck constant is %%md.math(hbar == hbar()), or %%md.math(hbar(unit = "J s")).
  ```

  > The reduced Planck constant is $\hbar = 1.055 \times 10^{-34}\ \mathrm{kg}\,\mathrm{m}^{2}\,\mathrm{s}^{-1}$, or $\hbar = 1.055 \times 10^{-34}\ \mathrm{J}\,\mathrm{s}$.

  When the `Variable` is used directly, its name is printed. When it is called, its value is formatted and printed (with units, where appropriate --  see [Units](#units)).

### Instantiating Several `Variable`s

Since it is common to instantiate several variables at once, an additional function is provided, `tex.symbols`. This function parses a string defining several variables, their values, and their units. It takes a string with a list of definitions, separated by either newlines or semicolons (`;`). Each definition can be a single variable, or a variable with a value and optionally units and a format specifier. For example:
```python
tex.symbols("""
    a;
    b = 3.4;
    c = 2.3 meter per second;
    d = 4.5 (.3f)
    e = 3.4e-3 kg m^2 / s (.2e)';
    f = 4; g = 3;
""")
```

The general syntax is `<name> = <value> <units> (<format>)`. This is equivalent to `tex.var('name', value, fmt = 'format', unit = 'units')`. As such, `name` can contain $\LaTeX{}$ syntax. Where `value` is an integer, it will be interpreted as such, rather than as a float. 

The function `tex.symbols` returns a tuple of the variables created. Additionally, it can take a second (optional) argument, `namespace`, which is a dictionary of variables which will be updated with the new variables. In this way, it can be used to create variables in the global (or local) namespace without needing to assign them individually. For example:
```python
tex.symbols("""
    a = 3;
    b = 4;
""", globals())
print(a <= b) 
# output: a \leq b
```

In this case, the `name` is transformed to be a valid Python variable name before being added to the namespace. Specifically, space (` `) and hyphen (`-`) characters are replaced with underscores (`_`), backslashes (`\`) and braces (`{`, `}`) are removed, and any remaining non-alpha-numeric characters are replaced with underscores. If the first character is not a letter, an underscore is prepended. This does not affect the name as it is typeset. For example,
```python
tex.symbols(r"""
    \alpha_{i} = 4;
""", globals())
print(alpha_i == alpha_i()) 
# output: \alpha_{i} = 4
```

## Printing Values

Additionally, most `Token`s are callable. This is mostly useful for instances of the `Variable` or `Quantity` classes, which keep track of a value (and units) through most operations. This is best seen through an example. We first instantiate three `Variable`s.
```markdown
%{
    a = tex.var("a", 3, unit = "cm")
    b = tex.var("b", 4, unit = "inch")
    c = tex.var("c", (a **2 + b ** 2)**0.5)
}
```

Note that when constructing the `c` variable, we are passing an expression as the value -- this will be automatically evaluated (with some exceptions; see [Expression Evaluation](#expression-evaluation)). Form more on units, see [Units](#units).

We can now write
```markdown
Pythagoras' theorem states that for a triangle with side lengths %%md.math(a), %%md.math(b), and %%md.math(c), the following relationship holds:
%%md.equation(
    a ** 2 + b ** 2 == c ** 2
)
```

This would be rendered as follows:

> Pythagoras' theorem states that for a triangle with side lengths $a$, $b$, and $c$, the following relationship holds:
> $${a} ^ {2} + {b} ^ {2} = {c} ^ {2}$$

We can now also write
```markdown
For example, if %%md.math(a == a()) and %%md.math(b == b()), then 
%%md.equation(
    ( c == tex.sqrt(a() ** 2 + b() ** 2) ) == c(unit = "cm")
)
```
> For example, if $a = 3\ \mathrm{cm}$ and $b = 4\ \mathrm{in}$, then
> 
> $$c = \sqrt{{\left( 3\ \mathrm{cm} \right)} ^ {2} + {\left( 4\ \mathrm{in} \right)} ^ {2}} = 10.59\ \mathrm{cm}$$

***Note:** I've encased everything before the second `==` in brackets -- see [Quirks](#quirks) to see why.*

### Formatting Numbers

When creating a `Quantity` or `Variable`, the format specifier can be passed as an optional argument, such as `fmt = '.3f'`. Then, when the object is called, this format specifier will be used to print the value. For example,
```markdown
%{
    import numpy as np
    pi = tex.var("\pi", 3.14159265358979323846, fmt = '.3f')
}

The value of $\pi$ is approximately %%md.math(pi()).
```
> The value of $\pi$ is approximately $3.142$.

Additionally, the `fmt` keyword argument can be passed to the `Quantity` or `Variable` when it is called to override the format specifier passed when the object was created. For example,
```markdown
A terrible approximation for $\pi$ is %%md.math(pi(fmt = '.0f')).
```
> A terrible approximation for $\pi$ is $3$.

The default format specifier for all `Quantity` and `Variable` objects can be set via the `tex.DEFAULT_FORMAT` variable. This is set to `'.4g'` by default, but can be changed at any time. 

#### Automatic Truncation

If no format specifier is provided (specifically through `fmt = ''`), the value is converted as though by `str()`. However, for floats there is an additional check -- if the value has more than $6$ decimal places and there is no format specifier, it is assumed that this is a floating point rounding error. The value is truncated to 6dp, and any trailing zeros are removed (including the decimal point if this results in an integer). This can be prevented by providing any format specifier. Additionally, this tolerance can be changed by setting the value of `tex.AUTO_TRUNCATE_LENGTH` (default 6). A negative `AUTO_TRUNCATE_LENGTH` will skip this check entirely.

### Units

The inclusion of units is more challenging from a technical perspective. If the output format is LaTeX-based, then the `siunitx` package covers all needs for typesetting units. However, for other formats this is not the case and often `siunitx` is incompatible. For example, for all HTML-based output formats, MathJax 3 does not have a plugin for `siunitx` (though MathJax 2 does, if you are able to configure that yourself).

Units are handled through the `pint` package. When a `Quantity` or `Variable` is created, it can be given a `unit` argument. This can be an instance of `pint.Unit` (through the registry available as `tex.ureg`), a valid `siunitx` string, or a string which can be parsed by `pint`. For example, any of the following are valid:
- `unit = tex.ureg.picometer`
- `unit = tex.ureg.parse_units("m/s")`
- `unit = r'\meter\per\second\squared'`
- `unit = 'kg m / s^2`

Thanks to `pint`'s excellent unit handling, units are preserved and propagated through most operations, automatically converting where necessary. This can be seen in the example in [Printing Values](#printing-values), where quanities in centimetres and inches are combined correctly. Units can be changed at any time:
```markdown
%{
    a = tex.Quantity(3, unit = "m / s")
    a.unit = "miles per hour"
}

The speed is %%md.math(a()).
```
> The speed is $6.711\ \mathrm{mi}\,\mathrm{h}^{-1}$.

Units can be converted when printing, by passing a `unit` argument to the `Quantity` or `Variable` when it is called. This will convert the value to the new unit, if possible. For example,
```markdown
%{
    eV = tex.Quantity(1, unit = "eV")
}

An energy of %%md.math(eV()) is equivalent to %%md.math(eV(unit = "J")).
```
> An energy of $1\ \mathrm{eV}$ is equivalent to $1.602 \times 10^{-19}\ \mathrm{J}$.

## Quirks

### Equality and Relational Operators

Because we are hijacking Python's relational operators for typesetting, they don't always act as expected. There are two specific cases where this is noticeable. Firstly, if the left-hand side of an equality (or other relational operator) is **not** a `Token`, then the order will be reversed when typesetting. For example, if `b` is a `Token` instance, then ``4 == b`` would be typeset as $b = 4$. This is because there is no way to distinguish between `a == b` and `b == a` in the same way as there is for `a + b` and `b + a` etc.

Secondly, repeated relational operators will not act as one might expect. Specifically, ``a == b == c`` does **not** produce $a = b = c$, since Python will try to optimise away some of the repeated comparisons. In order to achieve this result, one would need to encase one "comparison" in brackets. For example, ``a == (b == c)`` or ``(a == b) == c`` would both produce $a = b = c$.

### Expression Order

The order in which expressions are typeset is not changed when the expressions are evaluated. In other words, ``a * 4`` is rendered as $a4$, not the more natural $4a$. Although this module does make some efforts to be convenient for calculation, it's not intended to be a full symbolic maths library. For something with more advanced capabilities, consider using `sympy` directly.

### Expression Evaluation

Most operators will automatically calculate their value (assuming both operands have a value), appropriately converting units. The operators which do this are
- `a ** b`, $a^b$
- `a * b`, $a \times b$
- `a @ b`, $a \times b$
- `a / b`, $\frac{a}{b}$ and `a // b`, $\dfrac{a}{b}$ (note that these are *both* evaluated as true division)
- `a + b`, $a + b$
- `a - b`, $a - b$
- `+a` (unary), $a$ (does not change the value)
- `-a` (unary), $-a$
- `a == b`, `a <= b` etc, though evaluating these is generally not useful
- `tex.absolute(a)`, $|a|$

Additionally, an index does not change the value of the expression. For example, if `a` is a `Token` instance, then `a[2]` will be rendered as $a_2$, but will retain the same value as `a`. The same is true for any bracketed expression, such as `(a, )` or `{a}`. If these have a single child element, their value is the value of the child element. For brackets with multiple elements, the value will be `None`.
