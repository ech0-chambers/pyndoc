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
    tex.var("x") ** 3 + 2 == 11
)
```

Both produce

> $$x^{3} + 2 = 11$$

## Operators

Maths in Pyndoc is built around the abstract `Expression` class, which allows us to take advantage of Python's operator overloading. For binary operators (`+`, `==`, `/` etc), if either the left or right operand is an `Expression`, the result will be an `Expression` which constructs the appropriate LaTeX. All operators which are handled by the `Expression` class are listed below, in order of precedence (from highest to lowest).

| Operator                     | Example      | LaTeX                                  | Rendered                                | Description                                                                                                                                                                                                                                                                      |
|------------------------------|:------------:|----------------------------------------|:---------------------------------------:|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `(...)`                      | `(a + 2)`    | `{a+2}`                                | $a+2$                                   | Used just like in normal Python to control the order of evaluation                                                                                                                                                                                                               |
| `(… , )` (Tuple constructor) | `(a/b,)`     | `\left(\frac{a}{b}\right)`             | $\left(\dfrac{a}{b}\right)$             | A tuple with a single element is encased in (scalable) parentheses. Note that a tuple is constructed by the comma, not just by the parentheses.                                                                                                                                  |
| `[...]` (List constructor)   | `[a/b]`      | `\left[\frac{a}{b}\right]`             | $\left[\dfrac{a}{b}\right]$             | A list with a single element is encased in (scalable) square brackets                                                                                                                                                                                                            |
| `{...}` (Set constructor)    | `{a/b}`      | `\left\lbrace\frac{a}{b}\right\rbrace` | $\left\lbrace\dfrac{a}{b}\right\rbrace$ | A set with a single element is encased in (scalable) braces                                                                                                                                                                                                                      |
| `...[...]`                   | `a[b]`       | `{a}_{b}`                              | $a_b$                                   | An index will be treated as a subscript (assuming `a` is an `Expression` object)                                                                                                                                                                                                 |
| `**`                         | `a**2`       | `{a}^{2}`                              | $a^2$                                   | The exponentiation operator results in an exponent (superscript)                                                                                                                                                                                                                 |
| `+` (unary)                  | `+a`         | `+{a}`                                 | $+a$                                    | Unary plus and minus have the expected result.                                                                                                                                                                                                                                   |
| `-` (unary)                  | `-a`         | `-{a}`                                 | $-a$                                    |                                                                                                                                                                                                                                                                                  |
| `*`                          | `a*b`        | `a b`                                  | $ab$                                    | The standard multiplication operator is rendered as implicit multiplication                                                                                                                                                                                                      |
| `@`                          | `a@b`        | `a\times b`                            | $a \times b$                            | The matrix multiplication operator can be used when implicit multiplication would be ambiguous, and inserts a multiplication symbol ($\times$) between the expressions |
| `/`                          | `a/b`        | `\frac{a}{b}`                          | $\frac{a}{b}$                           | True division results in a fraction                                                                                                                                                                                                                                              |
| `//`                         | `a//b`       | `\dfrac{a}{b}`                         | $\dfrac{a}{b}$                          | Floor division forces a display-mode fraction, regardless of the math environment (using `\dfrac`)                                                                                                                                                                               |
| `+` (binary)                 | `a+b`        | `a+b`                                  | $a+b$                                   | Binary addition and subtraction have the expected result in the typeset equation. Note that this overrides the use of `+` for string concatenation if one of the operands is an Expression.                                                                                      |
| `-` (binary)                 | `a-b`        | `a-b`                                  | $a-b$                                   |                                                                                                                                                                                                                                                                                  |
| `&`                          | `a & “text”` | `a text`                               | $a text$                                | Since `+` is used for the addition operator, a bitwise AND has been repurposed for string concatenation. The `Expression` is converted to a string, then concatenated with the `str` as normal. Note that the result of this is another `str`, **not** an `Expression` object.   |
| `==`                         | `a == b`     | `a = b`                                | $a = b$                                 | Conditional tests in the Python code are statements in the LaTeX output.                                                                                                                                                                                                         |
| `<`                          | `a<b`        | `a < b`                                | $a < b$                                 |                                                                                                                                                                                                                                                                                  |
| `<=`                         | `a<=b`       | `a \leq b`                             | $a\leq b$                               |                                                                                                                                                                                                                                                                                  |
| `>`                          | `a>b`        | `a > b`                                | $a > b$                                 |                                                                                                                                                                                                                                                                                  |
| `>=`                         | `a>=b`       | `a \geq b`                             | $a\geq b$                               |                                                                                                                                                                                                                                                                                  |
| `!=`                         | `a!=b`       | `a \neq b`                             | $a\neq b$                               |                                                                                                                                                                                                                                                                                  |


## Printing Values

Additionally, `Expressions` are callable. This is mostly useful for instances of the `Variable` class, which keeps track of a value through most operations. This is best seen through an example. We first instantiate three `Variable`s.
```markdown
%{
    a = tex.var("a", 3)
    b = tex.var("b", 4)
    c = tex.var("c", (a **2 + b ** 2)**0.5)
}
```

Note that when constructing the `c` variable, we are passing an `Expression` as the value -- this will be automatically evaluated (with some exceptions; see [Expression Evaluation](#expression-evaluation)). We can now write
```markdown
Pythagoras' theorem states that for a triangle with side lengths %%md.math(a), %%md.math(b), and %%md.math(c), the following relationship holds:
%%md.equation(
    a ** 2 + b ** 2 == c ** 2
)
```

This would be rendered as follows:

> Pythagoras' theorem states that for a triangle with side lengths $a$, $b$, and $c$, the following relationship holds:
> $$a^{2} + b^{2} = c^{2}$$

We can now also write
```markdown
For example, if %%md.math(a == a()) and %%md.math(b == b()), then 
%%md.equation(
    ( c == tex.sqrt(a() ** 2 + b() ** 2) ) == c()
)
```
> For example, if $a = 3$ and $b = 4$, then
> 
> $$c = \sqrt{{3} ^ {2} + {4} ^ {2}} = 5$$

***Note:** I've encased everything before the second `==` in brackets -- see [Quirks](#quirks) to see why.*

### Formatting Numbers

When calling an `Expression` to print its value, we can optionally pass a format specifier which is used when printing the value. This is simply a standard Python format specifier:
```markdown
%{
    import numpy as np
    pi = tex.var("\pi", np.pi)
}

The value of $\pi$ is approximately %%md.math(pi('.3f')).
```
> The value of $\pi$ is approximately $3.142$.

In addition to the standard format specifiers, there is a special format specifier `el` (or `EL`) which will print the value in scientific notation using LaTeX syntax. For example,
```markdown
%%md.math(pi('.3el'))
```
> $3.142 \times 10^{0}$

#### Automatic Truncation

If no format specifier is provided, the value is converted as though by `str()`. However, for floats there is an additional check -- if the value has more than $6$ decimal places and there is no format specifier, it is assumed that this is a floating point rounding error. The value is truncated to 6dp, and any trailing zeros are removed (including the decimal point if this results in an integer). This can be prevented by providing any format specifier. Additionally, this tolerance can be changed by setting the value of `tex.AUTO_TRUNCATE_LENGTH` (default 6). A negative `AUTO_TRUNCATE_LENGTH` will skip this check entirely.

### Units

The inclusion of units is more challenging from a technical perspective. If the output format is LaTeX-based, then the `siunitx` package covers all needs for typesetting units. However, for other formats this is not the case and often `siunitx` is incompatible. For example, for all HTML-based output formats, MathJax 3 does not have a plugin for `siunitx` (though MathJax 2 does, if you are able to configure that yourself).

Despite this, `siunitx` is still the best tool for handling units and so that is what will be used for the forseeable future. In addition to the optional `format` argument, `Expression`s can take an optional `unit` argument. This should be a string which is a valid `siunitx` unit, such as `r"\meter\per\second"`. In most output formats, this will simply be converted to an `\SI` macro. For example,
```markdown
%{
    v = tex.var("v", 3)
}

The car moves at a speed of %%md.math(v(unit = r"\meter\per\second")).
```
> The car moves at a speed of $3\,\mathrm{m}\mathrm{s}^{-1}$.

***Note:** Here, I've manually typeset the unit so that it will display correctly on GitHub. The actual output would be ``The car moves at a speed of $\SI{3}{\meter\per\second}$``.*

If the output format is HTML-based, then the python package `pint` will be used to parse the unit string and convert it to a format which MathJax can typeset. In most cases, this will result in an almost identical output visually.

## Quirks

### Equality and Relational Operators

Because we are hijacking Python's relational operators for typesetting, they don't always act as expected. There are two specific cases where this is noticeable. Firstly, if the left-hand side of an equality (or other relational operator) is **not** an `Expression`, then the order will be reversed when typesetting. For example, if `b` is an `Expression` instance, then ``4 == b`` would be typeset as $b = 4$. This is because there is no way to distinguish between `a == b` and `b == a` in the same way as there is for `a + b` and `b + a` etc.

Secondly, repeated relational operators will not act as one might expect. Specifically, ``a == b == c`` does **not** produce $a = b = c$. In order to achieve this result, one would need to encase one "comparison" in brackets. For example, ``a == (b == c)`` or ``(a == b) == c`` would both produce $a = b = c$.

### Expression Order

The order in which expressions are typeset is not changed when the expressions are evaluated. In other words, ``a * 4`` is rendered as $a4$, not the more natural $4a$. Although this module does make some efforts to be convenient for calculation, it's not intended to be a full symbolic maths library. I leave that to much better programmers, such as the team behind `sympy`.

### Expression Evaluation

Most operators will automatically calculate their value (assuming both operands have a value). The operators which do this are
- `a ** b`, $a^b$
- `a * b`, $a \times b$
- `a @ b`, $a \times b$
- `a / b`, $\frac{a}{b}$ and `a // b`, $\dfrac{a}{b}$ (note that these are *both* evaluated as true division)
- `a + b`, $a + b$
- `a - b`, $a - b$
- `+a` (unary), $a$ (does not change the value)
- `-a` (unary), $-a$

Additionally, an index does not change the value of the expression. For example, if `a` is an `Expression` instance, then `a[2]` will be rendered as $a_2$, but will retain the same value as `a`.
