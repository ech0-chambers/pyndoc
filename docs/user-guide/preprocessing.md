# Preprocessing Directives

Pyndoc includes a build-time preprocessor that expands compact `%` directives into standard Pandoc code spans before Pandoc parses the document. This significantly reduces boilerplate when embedding variables, computations, and external files.

## Overview

When writing documents with dynamic Python content, standard Pandoc code attributes can quickly become verbose:

```markdown {.example title="Pure Markdown Syntax"}
`x = 25`{.py .quiet} The square root of `print(x)`{.py} is `import math; print(math.sqrt(x))`{.py}.
```

With the preprocessor enabled, the same document is written concisely:

```markdown {.example title="Inline Directives"}
%{
    import math
    x = 25
};
The square root of %x is %math.sqrt(x).
```

The preprocessor also enables features not available in standard Pandoc filters, such as recursive Markdown file inclusion and format-conditional document branching.

## Syntax & Directives

### Inline Expressions & Macros

* **Single Percent (`%expr`)**: Evaluates `expr`, automatically wraps it in `print()`, and tags it with class `{.py}`:
  - Variables: `%total`, `%data.price`
  - Function calls: `%calculate_mean(samples)`, `%time.strftime('%Y-%m-%d')`
  - Chained expressions: `%items[0].name.upper()`
  - Sentence-ending period protection: in `%user.name. Next sentence`, the period followed by space/newline is preserved as document punctuation rather than an invalid Python attribute access.
* **Format Specifiers (`%expr:spec`)**: Formats numbers and strings using standard Python format syntax:
  - `%price:.2f` $\to$ `` `print('{:.2f}'.format(price))`{.py} ``
  - `%ratio:.1%` $\to$ `` `print('{:.1%}'.format(ratio))`{.py} ``
  - `%code:>8s` $\to$ `` `print('{:>8s}'.format(code))`{.py} ``
* **Double Percent (`%%expr`)**: Evaluates an AST element without wrapping in `print()`, emitting class `{.py-md}`:
  - Used for Panflute elements, tables, lists, or LaTeX math tokens: `%%table`, `%%md.bold("Important")`.
* **Semicolon Suppression (`%expr;` or `%%expr;`)**: Appends a trailing semicolon to suppress output, emitting class `{.quiet}`:
  - `%db.connect();` or `%(counter += 1);`

### Code Blocks

Multi-line Python code blocks use bracketed directive syntax:

* **Single Block (`%{...}`)**: Emits a fenced code block with class `{.py}`. Standard output produced within the block is inserted into the document:
  ```markdown {.example}
  %{
    import numpy as np
    data = np.random.normal(0, 1, 1000)
    print(f"Sample variance: {data.var():.4f}")
  }
  ```
* **Double Block (`%%{...}`)**: Emits an AST block with class `{.py-md}`. The final expression or returned element is inserted directly into the Pandoc AST:
  ```markdown {.example title="Dynamic Markdown Table"}
  %%{
    import pyndoc.markdown as md
    md.table([["Item", "Quantity"], ["Apples", 12], ["Oranges", 7]])
  }
  ```
* **Quiet Block (`%{...};` or `%%{...};`)**: Appending a semicolon to the closing brace suppresses all output, making it ideal for imports and data preparation:
  ```markdown
  %{
    import pandas as pd
    df = pd.read_csv("measurements.csv")
    total_count = len(df)
  };
  ```

### File Inclusions

The preprocessor provides directives for modular document composition:

#### Python Scripts (`%%%py{...}`)

Executes an external Python script file and captures its standard output into the document (equivalent to `{.py-file}`):

```markdown
%%%py{scripts/generate_plots.py}
```

Appending a semicolon (`%%%py{scripts/setup.py};`) runs the script silently.

#### Markdown Files (`%%%md{...}`)

Recursively preprocesses and inlines an external Markdown file before passing the document to Pandoc:

```markdown
%%%md{sections/introduction.md}
```

Because inclusion occurs during preprocessing, all `%` directives within the included file are evaluated in the same shared document namespace.

#### Markdown Directories (`%%%mddir{...}`)

Includes all Markdown files (`.md`, `.markdown`) located in a specified directory, sorted alphabetically:

```markdown
%%%mddir{chapters/}
```

This is particularly useful for book-length documents or multi-part reports organized into numeric files (e.g. `01_intro.md`, `02_methods.md`, `03_results.md`).

#### Format-Conditional Files (`%%%mdifformat{...}`)

Includes specific Markdown files conditionally based on the active Pandoc target output format:

```markdown
%%%mdifformat{
    latex, beamer: includes/latex_layout.md;
    html, epub: includes/web_layout.md;
}
```

Whitespace and newlines within the directive are ignored. If the target format does not match any specified branch, no content is included.
