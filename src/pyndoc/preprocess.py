import io
from io import StringIO
from pathlib import Path
import re
import logging
import sys
from typing import List, Optional
from .formats import Format

TARGET_FORMAT = None

def deindent(code: str) -> str:
    # remove the indentation from the code block based on the first line
    code = code.replace("\t", " " * 4)
    lines = code.split("\n")
    if len(lines) == 0:
        return code
    indent = len(lines[0]) - len(lines[0].lstrip())
    out_lines = []
    for i, line in enumerate(lines):
        if len(line) < indent:
            if len(line.strip()) == 0:
                out_lines.append("")
                continue
            else:
                raise Exception(
                    f"Inconsistent indentation in code block at line {i+1}:\n"
                    + "-" * 80
                    + "\n"
                    + code
                    + "\n"
                    + "-" * 80
                )
        if line[:indent] == " " * indent:
            out_lines.append(line[indent:])
        else:
            raise Exception(
                f"Inconsistent indentation in code block at line {i+1}:\n"
                + "-" * 80
                + "\n"
                + code
                + "\n"
                + "-" * 80
            )
    return "\n".join(out_lines)


from rich.syntax import Syntax
from rich.style import Style
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich import print as rprint


def throw_parsing_error(contents: str, start: int, message: str, length: int = 1):
    error_line_number = get_line_number(contents, start)
    error_line_number += 1
    error_column_number = start - contents.rfind("\n", 0, start) - 1
    s = Syntax(
        contents,
        "markdown",
        line_numbers=True,
        highlight_lines=[error_line_number],
        line_range = (max(0, error_line_number - 2), min(len(contents.split("\n")), error_line_number + 2)),
        theme = "nord",
        word_wrap = True,
        indent_guides = True,
    )
    style = Style(bgcolor = "red", bold = True)
    s.stylize_range(style, (error_line_number, error_column_number), (error_line_number, error_column_number + length))
    
    t = Text(f"Preprocessor parsing error at line {error_line_number}: {message}.")
    g = Group(t, Panel(s, padding = 1))

    p = Panel(g, title = "Preprocessor parsing error")
    rprint(p)

    simple_text = contents.split("\n")[error_line_number - 2:error_line_number + 1]
    simple_text += [" " * error_column_number + "^" * length]
    simple_text += contents.split("\n")[error_line_number + 1:error_line_number + 3]
    simple_text = ">   " + "\n>   ".join(simple_text)
    raise Exception(f"Preprocessor parsing error at line {error_line_number}: {message}:\n\n" + simple_text)


def read_code(contents: str, start: int) -> tuple[int, str]:
    # Find the end of the code block, and return the number of characters to skip and the code block (including the opening and closing characters)
    # The opening character is at contents[start]
    delimiter = contents[start]
    if start >= len(contents) - 1:
        # this is the last character in the file. Just return the character. Something has probably gone wrong, but we'll let pandoc handle it
        return 1, delimiter
    if delimiter == "~" and contents[start + 1] != "~":
        # this isn't actually code. Just return the character
        return 1, delimiter

    if delimiter == "`" and contents[start + 1] != "`":
        # this is an inline code block. Just find the next non-escaped backtick
        i = start + 1
        while i < len(contents):
            if contents[i] == "\\":
                i += 1
            elif contents[i] == delimiter:
                return i - start + 1, contents[start : i + 1]
            i += 1
        # if we reach the end of the file, throw an error
        throw_parsing_error(contents, start, "Unterminated inline code block")
    if delimiter == "`" and contents[start + 2] != "`":
        # This is an inline code block, but with double backticks -- presumably it contains single backticks somewhere. Search similarly, but only close on double backticks
        i = start + 2
        while i < len(contents):
            if contents[i] == "\\":
                i += 1
            elif contents[i] == delimiter and contents[i + 1] == delimiter:
                return i - start + 2, contents[start : i + 2]
            i += 1
        # if we reach the end of the file, throw an error
        throw_parsing_error(contents, start, "Unterminated inline code block")
    # this is a code block. Find the next code block delimiter
    i = start + 3
    while i < len(contents):
        if contents[i] == "\\":
            i += 1
        elif (
            contents[i] == delimiter
            and contents[i - 1] == delimiter
            and contents[i - 2] == delimiter
        ):
            return i - start + 1, deindent(contents[start : i + 1])
        i += 1
    # if we reach the end of the file, throw an error
    throw_parsing_error(contents, start, "Unterminated code block")


def read_math(contents: str, start: int) -> tuple[int, str]:
    # Find the end of the math block, and return the number of characters to skip and the math block (including the opening and closing characters)
    # The opening character is at contents[start]
    delimiter = contents[start]
    if start >= len(contents) - 1:
        # this is the last character in the file. Just return the character. Something has probably gone wrong, but we'll let pandoc handle it
        return 1, delimiter
    if contents[start + 1] != "$":
        # this is inline maths. Just find the next non-escaped dollar sign
        i = start + 1
        while i < len(contents):
            if contents[i] == "\\":
                i += 1
            elif contents[i] == delimiter:
                return i - start + 1, contents[start : i + 1]
            i += 1
        # if we reach the end of the file, throw an error
        throw_parsing_error(contents, start, "Unterminated inline math block")
    # this is a math block. Find the next math block delimiter
    i = start + 2
    while i < len(contents):
        if contents[i] == "\\":
            i += 1
        elif contents[i] == delimiter and contents[i - 1] == delimiter:
            return i - start + 1, contents[start : i + 1]
        i += 1
    # if we reach the end of the file, throw an error
    throw_parsing_error(contents, start, "Unterminated math block")


def find_matching_bracket(contents: str, start: int, strict: bool = False, is_double: bool = False) -> int:
    # Find the matching bracket for the bracket at `start`
    # If `strict`, then strings are not considered, and the first bracket is returned
    bracket_map = {
        "(": ")",
        "{": "}",
        "{": "}",
        "[": "]",
        "<": ">",
    }
    opening = contents[start]
    closing = bracket_map[opening]
    count = 1
    i = start + 1
    if is_double and not contents[start + 1] == opening:
        throw_parsing_error(contents, start, f"Invalid double bracket. Expected '{opening}{opening}', got '{opening}{contents[start + 1]}'")
    while i < len(contents):
        c = contents[i]
        if c == "\\":  # skip the next character
            i += 2
            continue
        if not strict and c in ["'", '"']:
            i = find_string_end(contents, i) + 1
            continue
        if c == opening:
            if is_double:
                if contents[i + 1] == opening:
                    i += 1
                    count += 1
            else:
                count += 1
        elif c == closing:
            if is_double:
                if contents[i + 1] == closing:
                    i += 1
                    count -= 1
            else:
                count -= 1
        if count == 0:
            return i
        i += 1
    throw_parsing_error(contents, start, "Unterminated bracket")


def find_string_end(contents: str, start: int) -> int:
    delimiter = contents[start]
    if start >= len(contents):
        return start
    is_triple = False
    if contents[start + 1] == delimiter and contents[start + 2] == delimiter:
        # it is a triple-quoted string
        is_triple = True
    i = start + 1
    while i < len(contents):
        c = contents[i]
        if c == "\\":
            i += 2
            continue
        if c == delimiter:
            if not is_triple:
                return i
            if contents[i + 1] == delimiter and contents[i + 2] == delimiter:
                return i + 2
        i += 1
    throw_parsing_error(contents, start, "Unterminated string")


identifier_pattern = re.compile(r"(?P<name>\w[\w\d\.]*)(?P<next>[^\w\.]|$)")


def get_identifier(contents: str, start: int) -> tuple[int, str]:
    matched = identifier_pattern.match(contents, start)
    if matched is None:
        return 0, None
    name = matched.group("name")
    return len(name), name


format_specifier_pattern = re.compile(
    r"""
    :(?P<fill>.)?
    (?P<align>[><=^])?
    (?P<sign>[+\-\ ])?
    (?P<coerce>z)?
    (?P<alternate>\#)?
    (?P<zero_pad>0)?
    (?P<width>\d+)?
    (?P<grouping>[\_\,])?
    (?P<precision>\.\d+)?
    (?P<type>[bcdeEfFgGnosxX\%])?
""",
    re.X,
)


def get_format_specifier(contents: str, start: int) -> tuple[int, str]:
    matched = format_specifier_pattern.match(contents, start)
    if matched is None:
        return 0, None
    specifier = matched.group(0)
    if specifier.rstrip() == ":" or (
        matched.group("fill") == " " and matched.group("sign") == " " and matched.group("align") == None
    ):
        # this is a false positive which technically matches the pattern, but isn't supposed to be a format specifier
        return 0, None
    return len(specifier), specifier


def format_as_markdown(
    macro: str,
    is_double: bool,
    is_quiet: bool,
    is_solo: bool = False,
    is_inline: bool | None = None,
    specifier: Optional[str] = None,
) -> str:
    if not is_double and not is_quiet:
        if macro.startswith("print(") and macro.endswith(")"):
            macro = macro[6:-1]
        if specifier is not None:
            macro = f"print('{{{specifier}}}'.format({macro}))"
        else:
            macro = f"print({macro})"
    classes = ".py-md" if is_double else ".py"
    if is_quiet:
        classes += " .quiet"
    if is_inline is not None:
        classes += " .inline" if is_inline else " .block"
    if is_solo:
        return f"\n```{{{classes}}}\n{macro}\n```\n"
    return f"`` {macro} ``{{{classes}}}"
    


def get_line_number(string, index):
    # Returns the line number on which the `index`th character is found in the `string` (zero indexed).
    return string.count("\n", 0, index)


def is_only_text_on_line(string, start, end):
    # Returns True if the text between `start` and `end` is the only text on the line.
    # If there are multiple lines between start and end, returns true if there is no text on the line before start and no text on the line after end.
    # Returns False otherwise.

    start_line = get_line_number(string, start)
    end_line = get_line_number(string, end)
    lines = string.splitlines()
    start_in_line = start - len("\n".join(lines[:start_line])) - 1
    end_in_line = end - len("\n".join(lines[:end_line]))
    before = lines[start_line][:start_in_line]
    before_empty = before.strip() == ""
    after = lines[end_line][end_in_line:]
    after_empty = after.strip() == ""
    return before_empty and after_empty


def read_pyndoc_macro(contents: str, start: int) -> tuple[int, str]:
    # TODO: - Tidy this mess
    is_inline = None
    if contents[start] == "i":
        is_inline = True
    if contents[start] == "b":
        is_inline = False
    
    is_double = contents[start + (2 if is_inline is not None else 1)] == "%"
    is_quiet = False
    i = start + 2 if is_double else start + 1
    i += 1 if is_inline is not None else 0
    skip, macro_name = get_identifier(contents, i)
    i += skip
    if macro_name is None:
        throw_parsing_error(contents, start, "Invalid macro name")
    if macro_name.endswith("."):
        macro_name = macro_name[:-1]
        i -= 1
    if i == len(contents):
        # Just a variable name
        is_solo = is_only_text_on_line(contents, start, i - 1)
        return i - start, format_as_markdown(macro_name, is_double, is_quiet, is_solo, is_inline=is_inline)

    macro_string = StringIO()
    macro_string.write(macro_name)

    next_char = contents[i]
    if next_char == "{":
        # this is a raw macro.
        return read_pyndoc_raw_macro(contents, i, macro_name, is_double, is_inline)
    # Collect any arguments or indices, and any attributes or methods
    while next_char in ["(", "[", "."] and i < len(contents) - 1:
        if next_char == "(":
            bracket_end = find_matching_bracket(contents, i)
            skip = bracket_end - i + 1
            args = contents[i : bracket_end + 1]
            macro_string.write(args)
            i += skip
        elif next_char == "[":
            bracket_end = find_matching_bracket(contents, i)
            skip = bracket_end - i + 1
            args = contents[i : bracket_end + 1]
            macro_string.write(args)
            i += skip
        elif next_char == ".":
            i += 1
            skip, field = get_identifier(contents, i)
            if field is not None:
                macro_string.write("." + field)
                i += skip
            else:
                i -= 1
                break
        next_char = contents[i] if i < len(contents) else None
    macro_string = macro_string.getvalue()
    stripped = macro_string.strip()
    stripped_len = len(macro_string) - len(stripped)
    macro_string = stripped
    i -= stripped_len
    logging.debug(f"Macro string: {macro_string}")
    if macro_string.endswith("."):
        macro_string = macro_string[:-1]
        i -= 2
    
    if i < len(contents) and contents[i] == ":":  
        # format specifier
        skip, specifier = get_format_specifier(contents, i)
        if specifier is not None:
            i += skip
    else:
        specifier = None

    if i < len(contents) and contents[i] == ";":
        is_quiet = True
        i += 1
        
    is_solo = is_only_text_on_line(contents, start, i - 1)
    # i -= 1 # not 100% sure why this is necessary, but it seems to be
    return i - start, format_as_markdown(
        macro_string, is_double, is_quiet, is_solo, specifier=specifier, is_inline=is_inline
    )

def read_pyndoc_expression(contents: str, start: int) -> tuple[int, str]:
    # %%(a == b)
    
    is_inline = None
    if contents[start] == "i":
        is_inline = True
    if contents[start] == "b":
        is_inline = False
    
    is_double = contents[start + (2 if is_inline is not None else 1)] == "%"
    is_quiet = False
    i = start + 2 if is_double else start + 1
    i += 1 if is_inline is not None else 0
    # find closing bracket
    bracket_end = find_matching_bracket(contents, i)
    # Don't include the brackets in the expression
    macro_string = contents[i + 1 : bracket_end]
    i = bracket_end + 1
    stripped = macro_string.strip()
    stripped_len = len(macro_string) - len(stripped)
    macro_string = stripped
    # i -= stripped_len
    logging.debug(f"Macro string: {macro_string}")
    logging.debug(f"\tExtracted from: {contents[start:i]}")
    if i < len(contents) and contents[i] == ":":  
        # format specifier
        skip, specifier = get_format_specifier(contents, i)
        if specifier is not None:
            i += skip
    else:
        specifier = None

    if i < len(contents) and contents[i] == ";":
        is_quiet = True
        i += 1
    is_solo = is_only_text_on_line(contents, start, i - 1)
    return i - start, format_as_markdown(
        macro_string, is_double, is_quiet, is_solo, specifier=specifier, is_inline=is_inline
    )

def read_pyndoc_raw_macro(contents: str, start: int, macro_name: str, is_double: bool, is_inline: bool | None) -> tuple[int, str]:
    # %macro{arg1}{arg2}{{raw arg3}}{arg4}
    #     - transformed into a call to the python function `macro`
    #     - single `{` arguments are first run through `convert_from_string` with the final format specifier (to return a string)
    #     - double `{{` arguments are passed as strings, unchanged.
    #     - should return a string which is then included as raw
    # %%macro{arg1}{arg2}{{raw arg3}}{arg4}
    #     - same as above, but `{...}` are run through `convert_from_string` to convert to panflute elements instead of a string
    #     - should return a panflute element
    # We do not check for valid formatting within the arguments, so any mismatched `{` or `}` within the arguments *must* be escaped, even inside strings etc.
    # We also have the same quiet specifier as above.
    
    i = start
    start -= len(macro_name) + (2 if is_double else 1) + (1 if is_inline is not None else 0)
    # we're currently at the opening bracket
    next_char = contents[i]
    args = []
    # (arg_str, is_raw)
    while next_char == "{" and i < len(contents) - 1:
        next_char = contents[i + 1]
        is_raw = next_char == "{"
        arg_end = find_matching_bracket(contents, i, strict = False, is_double = is_raw)
        arg = contents[i + 1 : arg_end]
        if is_raw:
            arg = arg[1:-1]
        args.append((arg, is_raw))
        i = arg_end + 1
        next_char = contents[i] if i < len(contents) else None
    if i > len(contents):
        throw_parsing_error(contents, start, "Unterminated raw macro")
    
    if i < len(contents) and contents[i] == ":":  
        # format specifier
        skip, specifier = get_format_specifier(contents, i)
        if specifier is not None:
            i += skip
    else:
        specifier = None

    is_quiet = False
    if i < len(contents) and contents[i] == ";":
        is_quiet = True
        i += 1

    is_solo = is_only_text_on_line(contents, start, i - 1)

    macro_string = StringIO()
    macro_string.write(macro_name)
    macro_string.write("(")
    arg_strings = [
        'r"""' + arg.replace('"', '\\"') + '"""' if is_raw else
        'md.convert_from_string(r"""' + arg.replace('"', '\\"') + '""", True, md.TARGET_FORMAT.name.lower())'
        for arg, is_raw in args
    ]
    macro_string.write(", ".join(arg_strings))
    macro_string.write(")")
    skip, block =  i - start, format_as_markdown(
        macro_string.getvalue(), is_double, is_quiet, is_solo, specifier=specifier, is_inline=is_inline
    )
    logging.debug(f"Raw macro: {block}")
    return skip, block


def format_block_as_markdown(block: str, is_quiet: bool, is_solo: bool = False) -> str:
    classes = ".py"
    if is_quiet:
        classes += " .quiet"
    if is_solo:
        return f"\n```{{{classes}}}\n{block}\n```\n"
    return f"`` {block} ``{{{classes}}}"


def read_pyndoc_block(contents: str, start: int) -> tuple[int, str]:
    i = start + 1
    end = find_matching_bracket(contents, i)
    skip = end - start + 1
    block = contents[i + 1 : end]
    block = block.strip("\n")
    block = deindent(block)
    is_quiet = end + 1 < len(contents) and contents[end + 1] == ";"
    skip += 1 if is_quiet else 0
    is_solo = is_only_text_on_line(contents, start, start + skip - 1)
    return skip, format_block_as_markdown(block, is_quiet, is_solo)

# def capture_output(code):
#     """Captures the output of the code execution.

#     Args:
#         code: The Python code string to be executed.

#     Returns:
#         The captured output as a string.
#     """

#     code = deindent(code)
#     logging.debug("Running code:\n" + code)
#     old_stdout = sys.stdout
#     new_stdout = io.StringIO()
#     sys.stdout = new_stdout

#     try:
#         exec(code, globals())
#     except Exception as e:
#         logging.error(f"{e}")
#         sys.stdout = old_stdout
#         raise e
#     finally:
#         sys.stdout = old_stdout

#     out = new_stdout.getvalue()
#     # strip a single newline from the end of the output
#     if out.endswith("\n"):
#         out = out[:-1]
#     # if out.startswith("\n"):
#     #     out = out[1:]
#     return out

# md = object()

# def read_pyndoc_pre_block(contents: str, start: int) -> tuple[int, str]:
#     i = start + len("%%%pre")
#     end = find_matching_bracket(contents, i)
#     skip = end - start + 1
#     block = contents[i + 1 : end]
#     block = block.strip("\n")
#     block = deindent(block)
#     block = capture_output(block)
#     return skip, block


def read_pyndoc_file(contents: str, start: int, target_format: str) -> tuple[int, str]:
    i = start + 5
    end = find_matching_bracket(contents, i)
    skip = end - start + 1
    filename = contents[i + 1 : end]
    filename = filename.strip()
    filename = filename.replace("{format}", target_format)
    classes = ".py-file"
    is_solo = is_only_text_on_line(contents, start, start + skip - 1)
    is_quiet = end + 1 < len(contents) and contents[end + 1] == ";"
    if is_quiet:
        classes += " .quiet"
        skip += 1
    return skip, f"`` {filename} ``{{{classes}}}"


def read_pyndoc_md_file(contents: str, start: int, target_format: str) -> tuple[int, str]:
    # read the filename, open the file, preprocess it, and return the contents
    i = start + 5
    end = find_matching_bracket(contents, i)
    skip = end - start + 1
    filename = contents[i + 1 : end]
    filename = filename.strip()
    filename = filename.replace("{format}", target_format)
    file_path = Path(filename)
    if not file_path.exists():

        if not file_path.is_absolute():
            # if the file doesn't exist, check its parents up to the base directory until we find a directory which does exist
            base_dir = Path.cwd()
            current_path = file_path
            while not current_path.exists() and current_path != base_dir:
                current_path = current_path.parent
            
            if current_path == base_dir:
                throw_parsing_error(contents, start, f"File {filename} does not exist", length = skip)
            else:
                if current_path == file_path.parent:
                    # the file's parent exists, but the file doesn't
                    files = ", ".join([f.name for f in current_path.iterdir() if f.is_file()])
                    throw_parsing_error(contents, start, f"File {filename} does not exist, but its parent directory does. Files in {current_path}: {files}", length = skip)
                else:
                    # file was in a subdirectory which doesn't exist
                    dirs = ", ".join([d.name for d in current_path.iterdir() if d.is_dir()])
                    throw_parsing_error(contents, start, f"File {filename} does not exist. Parent directories down to {current_path} exist. Directories in {current_path}: {dirs}", length = skip)
        
    with file_path.open("r") as f:
        file_contents = f.read()
    file_contents = preprocess(file_contents, target_format)
    return skip, file_contents


def read_pyndoc_conditional_md_file(contents: str, start: int, target_format: str) -> tuple[int, str]:
    # %%%mdifformat{
    #     fmt1, fmt2: path/to/file1.md;
    #     fmt3: path/to/file2.md;
    #     fmt4: path/to/file3.md;
    # }
    #     - if the target format is fmt1 or fmt2, include the contents of file1.md
    #     - if the target format is fmt3, include the contents of file2.md
    #     - if the target format is fmt4, include the contents of file3.md
    #     - if the target format is not one of the specified formats, do not include any of the files

    i = start + len("%%%mdifformat")
    end = find_matching_bracket(contents, i)
    skip = end - start + 1
    options = [option.strip() for option in contents[i + 1 : end].split(";") if len(option.strip()) > 0]
    options = [option.split(":") for option in options]
    options = [(fmts.split(","), path) for fmts, path in options]
    options = [([fmt.strip().lower() for fmt in fmts], path.strip()) for fmts, path in options]
    for fmts, path in options:
        if target_format.lower() in fmts:
            file_path = Path(path)
            if not file_path.exists():
                throw_parsing_error(contents, start, f"File {path} does not exist", length = skip)
            with file_path.open("r") as f:
                file_contents = f.read()
            file_contents = preprocess(file_contents, target_format)
            return skip, file_contents
    return skip, ""

CHUNK_SIZES = [10_000, 5000, 2000, 1000, 500, 250, 100]

def contains_any(string: str, tests: List[str]) -> bool:
    for test in tests:
        if test in string: return True
    return False

def preprocess(contents: str, target_format: str | None = None) -> str:
    new_text = StringIO()
    i = 0
    len_contents = len(contents)
    check_chunks_idx = 0
    while i < len_contents:
        cont = False
        for CHUNK_SIZE in CHUNK_SIZES[check_chunks_idx:]:
            if i + CHUNK_SIZE < len_contents:
                if not contains_any(contents[i: i + CHUNK_SIZE], ["%", "<!--", '"', "'", "\\", "$"]):
                    new_text.write(contents[i:i + CHUNK_SIZE])
                    i += CHUNK_SIZE
                    cont = True
                    break
            else:
                check_chunks_idx += 1

        if cont:
            continue
        next_char = contents[i + 1] if i + 1 < len_contents else None
        c = contents[i]
        if contents[i:].startswith("<!--"):
            # this is the start of a comment. Skip until the end of the comment
            while not contents[i:].startswith("-->") and i < len_contents:
                i += 1
            i += 3
            continue
        if c == "\\":
            # escape character
            new_text.write(c)
            if next_char is not None:
                new_text.write(next_char)
                i += 1
            i += 1
            continue
        if c == "`":
            # (probably) a code block
            skip, code = read_code(contents, i)
            new_text.write(code)
            i += skip
            continue
        if c == "$":
            # (probably) a math block
            skip, math = read_math(contents, i)
            new_text.write(math)
            i += skip
            continue
        if re.match(r"[ib]?\%{1,2}\w", contents[i:]):
            # a pyndoc macro
            skip, replacement = read_pyndoc_macro(contents, i)
            new_text.write(replacement)
            i += skip
            continue
        if re.match(r"[ib]?\%{1,2}\(", contents[i:]):
            skip, replacement = read_pyndoc_expression(contents, i)
            new_text.write(replacement)
            i += skip
            continue
        if contents[i:].startswith("%{"):
            # a pyndoc block
            skip, replacement = read_pyndoc_block(contents, i)
            new_text.write(replacement)
            i += skip
            continue
        if contents[i:].startswith("%%%py{"):
            # a pyndoc file inclusion
            skip, replacement = read_pyndoc_file(contents, i, target_format)
            new_text.write(replacement)
            i += skip
            continue
        if contents[i:].startswith("%%%mdifformat"):
            # evaluated during preprocessing
            skip, block = read_pyndoc_conditional_md_file(contents, i, target_format)
            new_text.write(block)
            i += skip
            continue
        if contents[i:].startswith("%%%md"):
            # a pyndoc markdown file inclusion
            skip, replacement = read_pyndoc_md_file(contents, i, target_format)
            new_text.write(replacement)
            i += skip
            continue
        new_text.write(c)
        i += 1
    new_text = new_text.getvalue()
    new_text = re.sub(r"\n\n+", "\n\n", new_text)
    return new_text
