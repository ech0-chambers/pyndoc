# Getting Started

Pyndoc enables build-time Python execution, dynamic mathematical LaTeX AST generation, and structured Markdown output when building documents with Pandoc.

## Prerequisites

* **Python**: `>= 3.11`
* **Pandoc**: `>= 2.11`

Ensure Pandoc is installed and accessible on your system `PATH`:

```bash
pandoc --version
```

## Installation

Install Pyndoc using `pip` or your preferred package manager:

```bash
pip install pyndoc
```

Or using `uv`:

```bash
uv add pyndoc
```

## Quickstart

### 1. Create a Document

Create a file named `report.md`:

```{.example}
# Physics Lab Summary

%{
    # Set up physical parameters and formulas
    g = tex.var("g", 9.80665, fmt=".2f", unit="m / s^2")
    height = tex.var("h", 45.0, fmt=".1f", unit="m")
    t = tex.var("t", tex.sqrt(2 * height / g))
};

An object dropped from a height of %%height() experiences an acceleration of %%g().

The total time of flight is given by %%(t == t.expand), so:

%%md.equation(tex.split(
    [
        [t, t.expand],
        [t.expand()],
        [t()]
    ]
))
```

### 2. Compile with Pyndoc

Run the Pyndoc CLI driver with the `--preprocess` flag:

```bash
pyndoc --preprocess report.md -o report.html
```

Or generate a PDF via Pandoc's LaTeX engine:

```bash
pyndoc --preprocess report.md -o report.pdf
```

### 3. Alternative: Running as a Direct Filter

If your document uses standard Pandoc code classes (`.py`, `.py-md`) without `%` preprocessor macros, you can run `pandoc` directly:

```bash
pandoc --filter pyndoc-filter report.md -o report.html
```

## Next Steps

* Learn about all supported macro and inclusion directives in [Preprocessing Directives](preprocessing.md).
* Explore standard code block attributes and execution behavior in [Filter Execution](filter.md).
* Discover the full mathematical equation and unit generation system in [Mathematical Typesetting](math-typesetting.md).
* Learn how to generate structured tables, lists, and containers in [Markdown AST Generation](markdown-ast.md).
