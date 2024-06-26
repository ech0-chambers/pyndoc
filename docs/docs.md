# Documentation

## Running the Filter

Pyndoc can be used as a standard pandoc filter by passing it to the `--filter` option:
```bash
pandoc --filter /path/to/filter.py -o output.html input.md
```

When used in this way, the preprocessor is not available and so only standard markdown syntax is available. All functionality is available (if somewhat more verbose) without the preprocessor, except for the inclusion of other markdown files. 

Alternatively, Pyndoc can be used as a python module -- any arguments are passed to pandoc unchanged, except that the filter is automatically added (as the *first* filter if others are specified).
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
| `.py-md`   	| Evaluates the python code, which should return a `panflute.Element` object which is inserted into the pandoc AST before conversion to the output format.                              	| `` Find out more at `md.link(url)`{.py-md}`` |
| `.py-file` 	| Executes the contents of a Python file and collects any output to `stdout`, inserting the output verbatim in the final document.                                                      	| `` `path/to/myscript.py`{.py-file}`` |
| `.quiet`   	| Suppresses any output to `stdout`, allowing code to be executed without inserting anything into the final document. This should be used in conjunction with one of the other classes. 	| `` `script/with/output.py`{.py-file .quiet}`` |

These can be applied to code blocks or to inline code, such as `` `a=25`{.py} The square root of `print(a)`{.py} is `print(math.sqrt(a))`{.py} ``.

### Preprocessor Syntax

The preprocessor allows for much more compact syntax, and is enabled by passing the `--preprocess` option to the filter. It also allows for the inclusion of other markdown files, akin to the `\input{}` command in LaTeX. 

#### General Code

Python code can be included in the document with the syntax ``%{...}`` or ``%%{...}``. The former is the equivalent of a code block (or inline code) with the `.py` class, and the latter (double `%%`) is the equivalent of a code block with the `.py-md` class. This can include multiline code, single expressions, or expressions separated by semicolons.

Appending a semicolon such as `%{...};` or `%%{...};` will suppress the output of the code block, equivalent to the `.quiet` class.

#### Functions and Variables

The output of functions or values of variables can be included without the need to `print` them. If some variable `var` exists in Python, it can be included in the document with either `%var` (converted to a string before inclusion) or `%%var` (if `var` is a panflute element.) Functions can be included in much the same way: `%func(...)`, or `%%func(...)`. Again, appending a semicolon will suppress the output. All standard Python syntax is respected, so `%some_list[0]["callback"](arg1, func2("arg2"))` is valid and interpreted as expected, with strings correctly parsed (so you don't need to worry about escaping brackets within strings).

The preprocessor also allows for format specifiers, such as `%var:.2f` or `%func(...):0>8b`. *Almost* all python format specifiers are supported, except when the `fill` character and the `sign` character are both a space, and the `align` character is not specified (such as `:  f`) -- this is technically a valid python format specifier, but is assumed to be a false positive in the context of the preprocessor. A colon with no other format specifier will be interpreted as a literal colon, so `%%var:` will include the value of `var` followed by a colon.

#### Including Files

Python files and markdown files can be included with `%%%py{file_path}` and `%%%md{file_path}` respectively. The path is relative to the current working directory. For markdown files, the file is preprocessed, then included prior to the call to pandoc -- this means it is identical to directly including the file's content in the original document. 

For python files, the file is executed and any output is included in the document. It is the exact equivalent of `` `file_path`{.py-file} ``. A semicolon will, as normal, suppress the output.

