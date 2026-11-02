# Filter Execution

Pyndoc operates as a native Pandoc filter by analyzing code blocks and inline code elements within the Pandoc abstract syntax tree (AST). When used without preprocessing, Pyndoc requires only standard Pandoc Markdown syntax with specific class attributes.

## Overview

When Pandoc processes a document with the Pyndoc filter, code blocks tagged with special classes are evaluated in Python. Any output produced or elements returned are incorporated into the document before Pandoc converts it to the final output format (HTML, PDF, LaTeX, DOCX, etc.).

Pyndoc can be supplied directly to Pandoc as a filter:

```bash
pandoc --filter pyndoc-filter document.md -o output.html
```

When invoked this way, only standard Markdown syntax is supported (the `%` preprocessor syntax is not available).

## Standard Markdown Code Classes

Pyndoc identifies code to execute using four class attributes applied to fenced code blocks or inline code spans:

| Class | Purpose | Inline Example |
| :--- | :--- | :--- |
| `.py` | Executes Python code, captures standard output (`stdout`), and injects the output text verbatim into the document. | `` `print(math.pi)`{.py} `` |
| `.py-md` | Evaluates a Python expression or block returning a `panflute.Element` (or coercible object) and splices it directly into the document AST. | `` `md.link("Docs", "https://example.com")`{.py-md} `` |
| `.py-file` | Executes an external Python script file and captures its `stdout` output into the document. | `` `scripts/generate_data.py`{.py-file} `` |
| `.quiet` | Suppresses `stdout` output. Used in combination with `.py` or `.py-file` to define variables, import libraries, or perform computations silently. | `` `total = 42`{.py .quiet} `` |

### `.py` (Standard Execution)

The `.py` class executes the code and collects any text written to `stdout` (e.g. via `print()`):

````markdown {.example title="Standard Code Block (.py)"}
```{.py}
import math
radius = 5.0
area = math.pi * radius**2
print(f"A circle with radius {radius} has area {area:.2f}.")
```
````

This can also be applied inline:

```markdown
The value of $\pi$ is `print(f"{math.pi:.4f}")`{.py}.
```

### `.py-md` (AST Injection)

The `.py-md` class evaluates Python code and expects a Panflute AST element (such as a paragraph, table, list, or mathematical formula). Instead of inserting raw text, Pyndoc inserts the constructed AST node directly into Pandoc's document tree:

````markdown {.example title="AST List Injection (.py-md)"}
```{.py-md}
import pyndoc.markdown as md
md.bullet_list(["First item", "Second item", "Third item"])
```
````

### `.py-file` (Script Execution)

The `.py-file` class executes the contents of an external Python script file relative to the working directory and inserts any standard output verbatim:

```markdown
`scripts/generate_report.py`{.py-file}
```

If the script should execute silently (for instance, to set up variables or database connections), add the `.quiet` class:

```markdown
`scripts/setup_environment.py`{.py-file .quiet}
```

### `.quiet` (Silent Execution)

The `.quiet` class suppresses all `stdout` output. This allows importing modules, initializing state, or defining helper functions without leaving unwanted text in the final document:

````markdown
```{.py .quiet}
import numpy as np
samples = np.random.normal(loc=0.0, scale=1.0, size=1000)
mean_val = samples.mean()
```
````

The computed `mean_val` can then be referenced later in the document:

```markdown
Sample mean: `print(f"{mean_val:.3f}")`{.py}.
```

## Execution Namespace & State Persistence

All code executed within a document shares a persistent global namespace throughout the AST traversal:

1. **State Persistence**: Variables, functions, and imported modules defined in earlier code blocks remain available in all subsequent code blocks across the document.
2. **Pre-imported Modules**: The filter automatically populates the document namespace with convenient defaults:
   - `md`: The `pyndoc.markdown` submodule for constructing Pandoc AST elements.
   - `tex`: The `pyndoc.latex` submodule for mathematical AST generation and physical units.
   - `TARGET_FORMAT`: The active Pandoc output format string (e.g. `"html"`, `"latex"`, `"pdf"`).

## Strict Error Handling

By default, Pyndoc catches execution errors, formats a rich diagnostic error message to stderr, and inserts an error indicator into the document. If you wish the build process to immediately abort on the first error, you can enable strict mode by setting the environment variable:

```bash
export PYNDOC_STRICT=1
```
