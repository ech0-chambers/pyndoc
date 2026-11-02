# User Guide


---

## Guide Sections

### [Getting Started](getting-started.md)
Prerequisites, installation, CLI usage, and an end-to-end example demonstrating how Pyndoc coordinates with Pandoc.

### [Code Embedding](filter.md)
Detailed walkthrough of code embedding through tagged markdown code blocks.

### [Preprocessing Directives](preprocessing.md)
Comprehensive guide for the compact preprocessor syntax as well as external file inclusions.  

### [Mathematical Typesetting](math-typesetting.md)
How to construct dynamic LaTeX equations using natural Python syntax. Pyndoc provides easy handling of symbolic variables, which can also store a value and units. Units are conserved and converted through mathematical operations, and a convenient formatting syntax is defined.

### [Markdown AST Generation](markdown-ast.md)
Covers the markdown helper library for conveniently constructing various page elements including text formatting, lists, and tables. Inserted directly into the document AST, these are automatically converted to the output format alongside the rest of the document. 
