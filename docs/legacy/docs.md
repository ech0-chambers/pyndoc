# Documentation

## Running the Filter

Pyndoc can be used as a standard Pandoc filter by passing it to the `--filter` option:
```bash
Pandoc --filter /path/to/filter.py -o output.html input.md
```

When used in this way, the preprocessor (see [Preprocessor Syntax](#preprocessor-syntax)) is not available and so only standard markdown syntax is supported. All functionality is available (if somewhat more verbose) without the preprocessor, except for the inclusion of other markdown files. 

Alternatively, Pyndoc can be used as a python module -- any arguments are passed to Pandoc unchanged, except that the filter is automatically added (as the *first* filter if others are specified).
```bash
python3 -m pyndoc -o output.html input.md
```

When called in this way, the preprocessor is available via the `--preprocess` option:
```bash
python3 -m pyndoc --preprocess -o output.html input.md
```

## Syntax

### Standard Markdown Syntax

Pyndoc does not require any special syntax outside of the standard Pandoc-flavour markdown syntax. Code to execute is identified by applying one of three classes to a code block. For example
~~~
```{.py}
print("Hello, World!")
```
~~~
will execute the code `print("Hello, World!")`, collect the output (`Hello, World!`), and insert it verbatim into the final document. The classes of note are

| Class      	| Purpose                                                                                                                                                                               	| Example   |
|------------	|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------	|--------   |
| `.py`      	| Executes the python code and collects any output to `stdout`, inserting the output verbatim in the final document.                                                                    	| `` The value of $\pi$ is `print(np.pi)`{.py}`` |
| `.py-md`   	| Evaluates the python code, which should return a `panflute.Element` object which is inserted into the Pandoc AST before conversion to the output format.                              	| `` Find out more at `md.link(url)`{.py-md}`` |
| `.py-file` 	| Executes the contents of a Python file and collects any output to `stdout`, inserting the output verbatim in the final document.                                                      	| `` `path/to/myscript.py`{.py-file}`` |
| `.quiet`   	| Suppresses any output to `stdout`, allowing code to be executed without inserting anything into the final document. This should be used in conjunction with one of the other classes. 	| `` `script/with/output.py`{.py-file .quiet}`` |

These can be applied to code blocks or to inline code, such as `` `a=25`{.py} The square root of `print(a)`{.py} is `print(math.sqrt(a))`{.py} ``.

### Preprocessor Syntax

The preprocessor allows for much more compact syntax, and is enabled by passing the `--preprocess` option to the filter. It also allows for the inclusion of other markdown files, akin to the `\input{}` command in LaTeX. 

For example, without the preprocessor one might write

```markdown
`a=25`{.py} The square root of `print(a)`{.py} is `print(math.sqrt(a))`{.py}.
```

With the preprocessor, this becomes

```markdown
%{a=25} The square root of %a is %math.sqrt(a).
```

In both cases, the output is
> The square root of 25 is 5.0.

#### General Code

Python code can be included in the document with the syntax ``%{...}`` or ``%%{...}``. The former is the equivalent of a code block (or inline code) with the `.py` class, and the latter (double `%%`) is the equivalent of a code block with the `.py-md` class. This can include multiline code, single expressions, or expressions separated by semicolons.

Appending a semicolon such as `%{...};` or `%%{...};` will suppress the output of the code block, equivalent to the `.quiet` class.

#### Functions and Variables

The output of functions or the values of variables can be included without the need to `print` them. If some variable `var` exists in Python, it can be included in the document with either `%var` (converted to a string before inclusion) or `%%var` (if `var` is a panflute element). Functions can be included in much the same way: `%func(...)`, or `%%func(...)`. Again, appending a semicolon will suppress the output. All standard Python syntax is respected, so `%some_list[0]["callback"](arg1, func2("arg2"))` is valid and interpreted as expected, with strings correctly parsed (so you don't need to worry about escaping brackets etc within strings).

The preprocessor also allows for format specifiers, such as `%var:.2f` or `%func(...):0>8b`. *Almost* all python format specifiers are supported, except when the `fill` character and the `sign` character are both a space, and the `align` character is not specified (such as `:  f`) -- this is technically a valid python format specifier, but is assumed to be a false positive in the context of the preprocessor. A colon with no other format specifier will be interpreted as a literal colon, so `%var:` will include the value of `var` followed by a colon.

#### Including Files

Python files and markdown files can be included with `%%%py{file_path}` and `%%%md{file_path}` respectively (*only* when using the preprocessor). The path is relative to the current working directory. For markdown files, the file is preprocessed, then included prior to the call to Pandoc -- this means it is identical to directly including the file's content in the original document. Additionally, markdown files can be included conditionally based on the target format. This is achieved with the `%%%mdifformat` command. The syntax is as follows:

```markdown
%%%mdifformat{
    latex, beamer: path/to/latex/file.md;
    html: path/to/html/file.md;
}
```

This would include `path/to/latex/file.md` if Pandoc's target format is `latex` or `beamer`, and `path/to/html/file.md` if the target format is `html`. All whitespace and newlines are ignored. If the target format is not listed, no files are included. Just as with `%%%md{...}`, the file is preprocessed, then included before the call to Pandoc, so it is as if the file's content were directly included in the original document.

For python files, the file is executed and any output is included in the document. It is the exact equivalent of `` `file_path`{.py-file} ``. A semicolon will, as normal, suppress the output.

## Panflute elements

Any `.py-md` blocks expect to evaluate to a single Panflute element. Constructing such elements from scratch can be quite verbose and fiddly (since Panflute generally is not designed to be constructed manually, only modified). To counteract this, a module `markdown.py` is automatically imported into filter and so is available in any python code in the documents, under the alias `md`. This module provides a number of helper functions to simplify the creation of Panflute elements. See the [documentation](markdown.md) for more information.

### Note: Tables

Most features are implemented in this module, with the notable exception of tables. Currently, tables should be created by directly using the Panflute API. This will be addressed in a future update.

## Maths

Pyndoc does not disturb the normal maths syntax in markdown, even with the preprocessor enabled. However, since maths is parsed separately by Pandoc, it is not possible to include the output of python code in standard maths environments. One could not, for example, write ``We can approximate $\pi$ as $\pi \approx %np.pi:.2f$`` (or the non-preprocessor equivalent). 

Instead, when Python variables or functions should be included in maths, a `.py-md` block should be used to construct a Panflute Math element. To help with this, a module `latex.py` is available under the alias `tex` with a series of convenience functions and classes to make writing maths as natural as possible. See the [documentation](maths.md) for more information.

For example (using the preprocessor syntax),

```markdown
%{
    p_i, eps_i, k, T, j, eps_j, M = tex.symbols("p_i; \\epsilon_i; k; T; j; \\epsilon_j; M")
}

The Boltzmann distribution is given by

%%md.equation(
    p_i == tex.exp(- eps_i / (k * T)) / tex.sum(tex.exp(- eps_j / (k * T)), j == 1, M)
)
```

This would be rendered as (in the final document output)

> The Boltzmann distribution is given by
> 
> $$p_i = \frac{\exp\left(\frac{-{\epsilon} _ {i}}{k T}\right)}{\sum\limits_{j = 1}^{M}\exp\left(\frac{-{\epsilon} _ {j}}{k T}\right)}$$

Note that this is designed to be as close to standard Python syntax as possible -- division of variables results in a fraction in the output, multiplication results in multiplication, and so on. Of course, in this example there is no need to involve Pyndoc at all -- no part of the equation needs to be dynamically generated, and so this could be written using the normal markdown (LaTeX) maths syntax for the exact same result. See [the examples](examples/) for a more practical use case.