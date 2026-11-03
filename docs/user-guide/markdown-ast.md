# Markdown AST Generation

The `pyndoc.markdown` submodule (automatically imported as `md` in the document namespace) provides a Pythonic abstraction over Panflute and Pandoc AST construction.

## Overview

While `.py` blocks inject raw text into the document, `.py-md` blocks allow injecting native Pandoc AST elements. Generating AST elements directly guarantees valid Pandoc structure, avoids manual Markdown escaping, and supports rich formatting like multi-alignment tables, nested lists, and custom containers.

Every constructor in `pyndoc.markdown` includes automatic type coercion: strings, numbers, LaTeX tokens, and nested collections are converted into appropriate Panflute inline or block elements automatically.

## Tables

The `md.table()` function builds Pandoc `Table` elements from nested Python lists or dictionaries:

```python
import pyndoc.markdown as md

table = md.table(
    rows=[
        ["Alice", 28, "Engineer"],
        ["Bob", 34, "Designer"],
        ["Charlie", 22, "Student"],
    ],
    headers=["Name", "Age", "Role"],
    alignment=["left", "center", "left"],
    caption="Team Overview",
)
```

In directive syntax:

```markdown
%%md.table(
    rows=[["Mercury", 0.387], ["Venus", 0.723], ["Earth", 1.0]],
    headers=["Planet", "Distance (AU)"],
    alignment=["left", "right"],
)
```

Alignments can be passed as strings (`"left"`, `"right"`, `"center"`, `"default"`) or via the `Alignment` enum.

## Lists & Sublists

Constructing nested and formatted lists is supported through intuitive list helpers. Nested sublists can be passed directly as `(parent_label, [child_items])` pairs, and their type automatically defaults to match the parent list's type (e.g. nested lists in an `ordered_list` default to ordered sublists).

### List Type Control (`inner_list_type` & `ListType`)

All list constructors and [`list_item`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/markdown/lists.py) accept an optional `inner_list_type` parameter taking a [`ListType`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/markdown/lists.py) enum (`ListType.BULLET`, `ListType.ORDERED`, `ListType.DEFINITION`, or string equivalents `"bullet"`, `"ordered"`, etc.). When `None`, nested sublists inherit the parent list's type:

- [`ordered_list`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/markdown/lists.py) defaults inner lists to `ListType.ORDERED`.
- [`bullet_list`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/markdown/lists.py) defaults inner lists to `ListType.BULLET`.
- [`definition_list`](file:///home/echo/Documents/python_github/pyndoc/src/pyndoc/markdown/lists.py) defaults inner lists to `ListType.DEFINITION`.

### Bullet Lists (`bullet_list` / `unordered_list`)

```python
md.bullet_list([
    "Item 1",
    ("Item 2 with sublist", ["Subitem A", "Subitem B"]),
    "Item 3",
])
```

### Ordered Lists (`ordered_list`)

```python
md.ordered_list([
    "Step 1: Install",
    ("Step 2: Configure", [
        "Create configuration file",
        "Set environment variables",
    ]),
    "Step 3: Run",
])
```

To nest bullet lists inside an ordered list, specify `inner_list_type`:

```python
md.ordered_list(
    [
        "Step 1: Install",
        ("Step 2: Dependencies", ["Python >= 3.11", "Pandoc >= 3.0"]),
        "Step 3: Run",
    ],
    inner_list_type=md.ListType.BULLET,
)
```

### Definition Lists (`definition_list`)

```python
md.definition_list({
    "Term A": "Definition of Term A",
    "Term B": ["First definition", "Second alternative definition"],
    "Term C": ("Steps", ["Step 1", "Step 2"]),
}, inner_list_type=md.ListType.ORDERED)
```

## Block Elements

Common block-level structures can be generated dynamically:

* `md.paragraph(*inlines)`: Creates a standard paragraph block.
* `md.header(content, level=1)`: Creates a heading element of the specified level (1–6).
* `md.block_quote(*blocks)`: Wraps contents in a Markdown block quote (`>`).
* `md.code_block(code, language="python")`: Emits a syntax-highlighted code block.
* `md.div(*blocks, classes=..., attributes=...)`: Wraps content in a Pandoc Div container (useful for CSS classes, columns, or custom output styling).
* `md.horizontal_rule()`: Inserts a horizontal rule (`---`).

## Inline Elements

Inline constructors can be composed together or embedded inside block elements:

* `md.bold("Text")` / `md.italic("Text")` / `md.strikethrough("Text")`
* `md.code("sample_code")`
* `md.link("Link Title", "https://example.com")`
* `md.image("Alt Text", "assets/diagram.png", title="Diagram")`
* `md.inline_math("a^2 + b^2 = c^2")` / `md.math(...)`
* `md.equation(expr)`: Emits a display-mode mathematical equation block ($$).
* `md.span(*inlines, classes=..., attributes=...)`: Creates an inline span container with custom classes or attributes.
