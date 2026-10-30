"""Preprocessor module for Pyndoc.

Transforms Markdown documents containing Pyndoc macro directives into standard
Pandoc-compatible Markdown with appropriate execution classes (.py, .py-md, .py-file).
"""

from __future__ import annotations

import io
import re
import shutil
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import NoReturn, Optional, Sequence

from rich.syntax import Syntax
from rich.style import Style
from rich.panel import Panel
from rich.text import Text
from rich.console import Group, Console
from rich import print as rprint

# ==============================================================================
# Exceptions & Diagnostic Error Reporting
# ==============================================================================


class PreprocessorError(Exception):
    """Base exception for all preprocessor-related errors."""

    pass


class PreprocessorParsingError(PreprocessorError):
    """Raised when encountering syntax or parsing errors within directives."""

    pass


class PreprocessingIndentationError(PreprocessorError):
    """Raised when encountering inconsistent indentation"""

    pass


class PreprocessingMixedTabsAndSpacesError(PreprocessorError):
    """Raised when encountering mixed tabs and spaces in indentation"""

    pass


# Module-level Rich console instance
_CONSOLE: Console | None = None


def get_console() -> Console | None:
    """Get the active module-level Rich Console, if one has been initialised."""
    return _CONSOLE


def set_console(console: Console | None) -> None:
    """Set the module-level Rich Console.

    Args:
        console: A Rich Console instance or None.
    """
    global _CONSOLE
    _CONSOLE = console


def reset_console() -> None:
    """Reset the module-level Rich Console to None."""
    global _CONSOLE
    _CONSOLE = None


def no_console() -> Console:
    """Disable Rich terminal output by directing the module-level console to an in-memory buffer.

    Returns:
        The newly configured in-memory Rich Console.
    """
    global _CONSOLE
    _CONSOLE = Console(file=io.StringIO())
    return _CONSOLE


def _format_windowed_line(
    line: str,
    col: int,
    length: int,
    max_width: int = 80,
) -> tuple[str, str]:
    """Slice a horizontal window around an error site to prevent terminal wrapping.

    Ensures that long code lines never wrap in narrow terminals, keeping the caret
    underline strictly aligned with the error site.

    Args:
        line: The text line containing the error.
        col: 0-indexed column offset where the error begins.
        length: Length in characters of the error token to underline.
        max_width: Maximum allowed width of the output line.

    Returns:
        A tuple of (windowed_line, caret_line) where len(windowed_line) <= max_width.
    """
    token_len = max(1, length)
    col = max(0, min(col, len(line)))

    if len(line) <= max_width:
        return line, " " * col + "^" * token_len

    ellipsis = "..."
    ellipsis_len = len(ellipsis)

    # Effective budget available between potential left and right ellipses
    budget = max(10, max_width - (2 * ellipsis_len))

    if token_len >= budget:
        # Token is wider than or equal to window budget; start window at col
        left = col
        right = min(len(line), left + budget)
    else:
        # Center the token within the budget window
        token_center = col + token_len // 2
        left = max(0, token_center - budget // 2)
        right = left + budget

        if right > len(line):
            right = len(line)
            left = max(0, right - budget)

        if left > col:
            left = col
            right = min(len(line), left + budget)

    has_left = left > 0
    has_right = right < len(line)

    prefix = ellipsis if has_left else ""
    suffix = ellipsis if has_right else ""
    windowed_text = prefix + line[left:right] + suffix

    adjusted_col = len(prefix) + (col - left)
    available_caret_space = max(1, len(windowed_text) - adjusted_col)
    adjusted_len = min(token_len, available_caret_space)

    caret_str = " " * adjusted_col + "^" * adjusted_len
    return windowed_text, caret_str


def get_line_number(text: str, index: int) -> int:
    """Calculate the 0-indexed line number corresponding to a character index in text.

    Args:
        text: The source document text.
        index: The character offset.

    Returns:
        0-indexed line number.
    """
    return text.count("\n", 0, index)


def raise_parsing_error(
    contents: str,
    start: int,
    message: str,
    length: int = 1,
    exception: type[Exception] = PreprocessorParsingError,
    console: Console | None = None,
) -> NoReturn:
    """Format and raise a diagnostic parsing error with Rich syntax-highlighted context.

    Args:
        contents: The full text being processed.
        start: Character index where the syntax error began.
        message: Descriptive error message explaining the failure.
        length: Number of characters to highlight at the error site.
        exception: The exception class to raise (defaults to PreprocessorParsingError).
        console: Optional Rich Console. If None, falls back to the module-level console.

    Raises:
        PreprocessorParsingError: Always raised with formatted context.
    """
    if console is None:
        console = _CONSOLE

    error_line_index = get_line_number(contents, start)
    error_line_number = error_line_index + 1
    error_column_number = start - contents.rfind("\n", 0, start) - 1

    lines = contents.splitlines()
    num_lines = len(lines)
    start_line_index = max(0, error_line_index - 2)
    end_line_index = min(num_lines, error_line_index + 3)

    if console is not None:
        # If a Rich console is available, pretty-print syntax-highlighted error panel
        s = Syntax(
            contents,
            "markdown",
            line_numbers=True,
            highlight_lines=[error_line_number],
            line_range=(start_line_index + 1, min(num_lines, error_line_index + 2) + 1),
            theme="nord",
            word_wrap=True,
            indent_guides=True,
        )

        style = Style(bgcolor="red", bold=True)
        s.stylize_range(
            style,
            (error_line_number, error_column_number),
            (error_line_number, error_column_number + length),
        )

        t = Text(f"Preprocessor parsing error at line {error_line_number}: {message}.")
        g = Group(t, Panel(s, padding=1))
        p = Panel(g, title="Preprocessor parsing error")
        console.print(p)

    # ASCII text fallback formatted with horizontal windowing to avoid terminal line-wrapping
    try:
        term_cols = shutil.get_terminal_size((80, 24))[0]
    except Exception:
        term_cols = 80
    max_width = max(40, term_cols - 6)

    error_line = lines[error_line_index] if error_line_index < num_lines else ""
    win_line, win_carets = _format_windowed_line(
        error_line, error_column_number, length, max_width=max_width
    )

    simple_lines = []
    for i in range(start_line_index, error_line_index):
        line = lines[i]
        simple_lines.append(line[: max_width - 3] + "..." if len(line) > max_width else line)

    simple_lines.append(win_line)
    simple_lines.append(win_carets)

    for i in range(error_line_index + 1, end_line_index):
        line = lines[i]
        simple_lines.append(line[: max_width - 3] + "..." if len(line) > max_width else line)

    simple_text = ">   " + "\n>   ".join(simple_lines)

    raise exception(
        f"Preprocessor parsing error at line {error_line_number}: {message}\n\n"
        + simple_text
    )


# ==============================================================================
# Domain Models & Directives
# ==============================================================================


class DirectiveKind(Enum):
    """Categories of preprocessor directives supported by Pyndoc."""

    VARIABLE = auto()  # %var or %%var
    FUNCTION_CALL = auto()  # %func(...) or %%func(...)
    EXPRESSION = auto()  # %(expr) or %%(expr)
    CODE_BLOCK = auto()  # %{ code } or %%{ code }
    PYTHON_FILE = auto()  # %%%py{path}
    MARKDOWN_FILE = auto()  # %%%md{path}
    CONDITIONAL_MD = auto()  # %%%mdifformat{ fmt: path; }


class OutputPlacement(Enum):
    """Explicit placement overrides for directives."""

    AUTO = auto()
    INLINE = auto()
    BLOCK = auto()


@dataclass(frozen=True)
class DirectiveSpec:
    """Parsed metadata for an inline macro or expression directive."""

    code: str
    is_double: bool
    is_quiet: bool
    placement: OutputPlacement = OutputPlacement.AUTO
    format_specifier: str | None = None
    is_solo: bool = False


# ==============================================================================
# Indentation & Text Utilities
# ==============================================================================


def deindent(code: str) -> str:
    """Remove common leading indentation from a multiline block of code.

    Normalizes tabs to 4 spaces and determines indentation depth based on the
    first non-empty line.

    Args:
        code: Multi-line string of Python code.

    Returns:
        De-indented code block string.

    Raises:
        PreprocessorError: If inconsistent indentation is encountered.
    """
    # 1. Replace tab characters with 4 spaces and split into lines
    # 2. Measure indentation of the first line (count of leading spaces)
    # 3. Strip that exact indentation from each subsequent line
    # 4. Throw PreprocessorError if a non-empty line has inconsistent/lesser indentation
    # 5. Rejoin and return cleaned lines
    lines = code.splitlines()

    def replace_tabs(string: str) -> tuple[str, bool | None]:
        # returns the line with consistent spaces/tabs, and a flag to indicate
        # that tabs were present
        m = re.search(r"\S", string)
        if not m:
            return "", None  # no non-whitespace characters, so we'll strip it entirely
        idx = m.start()
        indent = string[:idx]
        if "\t" in indent and " " in indent:
            raise PreprocessingMixedTabsAndSpacesError()
        if "\t" in indent:
            indent = indent.replace("\t", "    ")
            return indent + string[idx:], True
        return string, False

    has_tabs = None
    for i, line in enumerate(lines):
        lines[i], line_has_tabs = replace_tabs(line)
        if (
            has_tabs is not None
            and line_has_tabs is not None
            and has_tabs != line_has_tabs
        ):
            raise PreprocessingMixedTabsAndSpacesError()
        if line_has_tabs is not None:
            has_tabs = line_has_tabs

    first_non_empty_idx = next((i for i, s in enumerate(lines) if s != ""), None)
    if first_non_empty_idx is None:
        # This is an empty code block. Strange, but not an error.
        return ""

    indent_length = len(lines[first_non_empty_idx]) - len(
        lines[first_non_empty_idx].lstrip(" ")
    )

    for i, line in enumerate(lines):
        if len(line) == 0:
            continue
        if len(line) < indent_length or not line.startswith(" " * indent_length):
            raise PreprocessingIndentationError("Inconsistent indentation depth")
        lines[i] = line[indent_length:]

    return "\n".join(lines)


def is_only_text_on_line(text: str, start: int, end: int) -> bool:
    """Determine if a character span [start, end) is the solitary content on its line(s).

    Used to decide whether an expression should be rendered as a standalone
    fenced block (```) or inline backticks (``).

    Args:
        text: The full source string.
        start: Beginning index of the span.
        end: Ending index of the span.

    Returns:
        True if all characters preceding `start` and succeeding `end` on their
        respective lines are whitespace.
    """
    # 1. Locate start and end line boundaries using newlines around start and end
    # 2. Inspect characters preceding 'start' on the first line (must be whitespace only)
    # 3. Inspect characters following 'end' on the final line (must be whitespace only)
    # 4. Return True if both before and after are empty/whitespace
    line_start = text.rfind("\n", 0, start)
    line_end = text.find("\n", end)

    prefix_start = 0 if line_start == -1 else line_start + 1
    suffix_end = len(text) if line_end == -1 else line_end

    prefix = text[prefix_start:start]
    suffix = text[end:suffix_end]

    return prefix.strip() == "" and suffix.strip() == ""


# ==============================================================================
# Delimiter Scanners & Island Extractors
# ==============================================================================


def scan_delimiter_run(contents: str, start: int) -> int:
    if start >= len(contents):
        return 0
    delimiter = contents[start]
    cursor = start
    while cursor < len(contents) and contents[cursor] == delimiter:
        cursor += 1

    return cursor - start


def read_code_span(contents: str, start: int) -> tuple[int, str]:
    """Scan and skip existing Markdown code spans or fenced blocks.

    Ensures that Pyndoc syntax delimiters inside raw Markdown code blocks or
    inline backticks are ignored.

    Args:
        contents: Full document content.
        start: Offset pointing to opening delimiter (` or ~).

    Returns:
        A tuple of (number of characters consumed, verbatim code text).
    """
    if start >= len(contents):
        return 0, ""

    delimiter = contents[start]
    if delimiter not in ("`", "~"):
        return 0, ""

    # 1. Measure the length of the opening delimiter run
    fence_length = scan_delimiter_run(contents, start)

    # In Markdown, single or double tildes are strikethrough/subscript marks, not code blocks.
    # Only 3 or more tildes ('~~~') constitute a fenced code block.
    if delimiter == "~" and fence_length < 3:
        return 0, ""

    is_fenced_block = fence_length >= 3
    cursor = start + fence_length

    # 2. Scan forward for the matching closing delimiter run
    while cursor < len(contents):
        # Skip backslash-escaped characters
        if contents[cursor] == "\\":
            cursor += 2
            continue

        if not is_fenced_block and contents[cursor] == "\n":
            error_message = "Newline encountered while parsing inline code span"
            raise_parsing_error(
                contents, start, error_message, length=cursor - start - 1
            )

        if contents[cursor] == delimiter:
            run_start = cursor
            run_length = scan_delimiter_run(contents, cursor)

            # Check for a valid closing delimiter run:
            # - Inline code (` or ``): requires an exact run length match.
            # - Fenced code blocks (``` or ~~~): require a run length >= opening fence length.
            if (not is_fenced_block and run_length == fence_length) or (
                is_fenced_block and run_length >= fence_length
            ):
                end = run_start + run_length
                code_text = contents[start:end]

                return end - start, code_text

            cursor += run_length
            continue

        cursor += 1

    # 3. If EOF is reached without finding a matching closing delimiter, raise an error
    span_type = "block" if is_fenced_block else "span"
    error_message = f"Unterminated code {span_type}"

    raise_parsing_error(contents, start, error_message, length=fence_length)


def read_dollar_math_span(contents: str, start: int) -> tuple[int, str]:
    """Scan and skip existing Markdown math spans ($...$ or $$...$$).

    Args:
        contents: Full document content.
        start: Offset pointing to opening '$'.

    Returns:
        A tuple of (number of characters consumed, verbatim math text).
    """
    # 1. Check whether opening delimiter is inline ('$') or display ('$$')
    # 2. Scan forward for matching unescaped closing delimiter ('$' or '$$')
    # 3. Raise PreprocessorParsingError if closing delimiter is missing before EOF
    # 4. Return (consumed_character_count, verbatim_math_string)
    if start >= len(contents):
        return 0, ""

    delimiter = contents[start]
    if delimiter != "$":
        return 0, ""

    fence_length = scan_delimiter_run(contents, start)

    if fence_length > 2:
        # This isn't maths
        return 0, ""

    cursor = start + fence_length

    if (
        fence_length == 1
        and cursor < len(contents)
        and contents[cursor] in (" ", "\n", "\t")
    ):
        # a dollar sign followed by whitespace is not a recognised math block in
        # Pandoc's markdown.
        return 0, ""

    while cursor < len(contents):
        if contents[cursor] == "\\":
            cursor += 2
            continue

        if contents[cursor] == delimiter:
            run_start = cursor
            run_length = scan_delimiter_run(contents, cursor)

            if run_length == 1 and (
                contents[cursor - 1] in (" ", "\n", "\t")
                or (
                    cursor + 1 < len(contents)
                    and "0" <= contents[cursor + 1] <= "9"
                )
            ):
                # A dollar sign preceded by a space or followed by a digit is
                # not recognised as a terminating delimiter in Pandoc's
                # markdown. Therefore, we were never in math mode to start with
                return 0, ""

            if fence_length == run_length:
                end = run_start + run_length
                math_text = contents[start:end]
                return end - start, math_text

            cursor += run_length

            continue

        if fence_length == 1 and contents.startswith("\n\n", cursor):
            # Inline math cannot cross paragraph breaks; starting '$' was literal text
            return 0, ""

        cursor += 1

    if fence_length == 1:
        # Unclosed inline '$' before EOF is treated as literal text in Markdown
        return 0, ""

    error_message = "Unterminated display math environment"
    raise_parsing_error(contents, start, error_message, length=fence_length)


def read_bracket_math_span(contents: str, start: int) -> tuple[int, str]:
    if start >= len(contents) - 1:
        return 0, ""

    if contents[start] != "\\" or contents[start + 1] not in ["(", "["]:
        # This isn't the start of math mode
        return 0, ""

    opening = contents[start + 1]
    closing = ")" if opening == "(" else "]"

    cursor = start + 2

    while cursor < len(contents) - 1:
        if contents[cursor] == "\\":
            if contents[cursor + 1] == closing:
                return cursor + 2 - start, contents[start : cursor + 2]
            cursor += 2
            continue

        cursor += 1

    span_type = "inline" if opening == "(" else "display"
    error_message = f"Unterminated {span_type} math environment"

    raise_parsing_error(contents, start, error_message, length=2)


def read_string_span(contents: str, start: int) -> tuple[int, str]:
    """Scan and return a Python string literal starting at `start`.

    Supports single-quoted ('...', "...") and triple-quoted ('''...''', \"\"\"...\"\"\")
    string literals, respecting backslash escapes.

    Args:
        contents: Full document content.
        start: Offset pointing to opening quote (' or ").

    Returns:
        A tuple of (number of characters consumed, verbatim string text).
    """
    if start >= len(contents):
        return 0, ""

    delimiter = contents[start]
    if delimiter not in ("'", '"'):
        return 0, ""

    # Check for triple-quoted string vs single-quoted string
    is_triple = contents.startswith(delimiter * 3, start)
    fence_length = 3 if is_triple else 1
    cursor = start + fence_length

    while cursor < len(contents):
        # Skip backslash-escaped characters
        if contents[cursor] == "\\":
            cursor += 2
            continue

        # In Python, single-quoted strings cannot span unescaped newlines
        if not is_triple and contents[cursor] == "\n":
            error_message = (
                "Unterminated string literal (newline in single-quoted string)"
            )
            raise_parsing_error(contents, start, error_message, length=fence_length)

        if contents[cursor] == delimiter:
            if is_triple:
                if contents.startswith(delimiter * 3, cursor):
                    end = cursor + 3
                    return end - start, contents[start:end]
            else:
                end = cursor + 1
                return end - start, contents[start:end]

        cursor += 1

    span_type = "multiline string" if is_triple else "string literal"
    error_message = f"Unterminated {span_type}"
    raise_parsing_error(contents, start, error_message, length=fence_length)


def read_comment_span(contents: str, start: int) -> tuple[int, str]:
    """Scan and return an HTML comment span (<!-- ... -->).

    Args:
        contents: Full document content.
        start: Offset pointing to opening '<'.

    Returns:
        A tuple of (number of characters consumed, verbatim comment text).
    """
    if start >= len(contents) or not contents.startswith("<!--", start):
        return 0, ""

    end = contents.find("-->", start + 4)
    if end == -1:
        # Unterminated comment extends to end of text
        return len(contents) - start, contents[start:]

    end += 3
    return end - start, contents[start:end]


def find_matching_bracket(
    contents: str,
    start: int,
    strict: bool = False,
    is_double: bool = False,
) -> int:
    """Find the index of the closing bracket matching the opening bracket at `start`.

    Respects nested brackets, escape sequences, and string literals (single, double,
    and triple quoted) unless `strict` is True.

    Args:
        contents: Document text.
        start: Index of the opening bracket ('(', '{', '[', '<').
        strict: When True, ignores string boundaries and matches brackets naively.
        is_double: When True, expects double brackets ('{{' and '}}').

    Returns:
        Character index of the corresponding closing bracket.

    Raises:
        PreprocessorParsingError: If closing bracket is missing or unterminated.
    """
    # 1. Map opening bracket at start to its corresponding closing bracket
    # 2. Initialize depth counter at 1 and advance through characters
    # 3. Skip escaped characters ('\\') and advance past string literals (find_string_end) unless strict
    # 4. Increment depth on opening bracket; decrement on closing bracket (handling single/double)
    # 5. When depth reaches 0, return index; raise PreprocessorParsingError if EOF reached
    bracket_map = {"(": ")", "{": "}", "[": "]", "<": ">"}
    opening = contents[start]
    closing = bracket_map[opening]

    span_map = {
        "'": read_string_span,
        '"': read_string_span,
        "`": read_code_span,
        "~": read_code_span,
        "$": read_dollar_math_span,
        "\\": read_bracket_math_span,
        "<": read_comment_span,
    }

    depth = 1
    cursor = start + (2 if is_double else 1)

    while cursor < len(contents):
        char = contents[cursor]

        if not strict:
            # skip code sections, maths sections, string sections.
            if char == "#":
                # Python comment
                newline_position = contents.find("\n", cursor)
                cursor = (
                    len(contents) if newline_position == -1 else newline_position + 1
                )
                continue

            if char in span_map:
                consumed, _ = span_map[char](contents, cursor)
                if consumed > 0:
                    cursor += consumed
                    continue

        if char == "\\":
            cursor += 2
            continue

        bracket_length = 2 if is_double else 1
        if contents.startswith(opening * bracket_length, cursor):
            depth += 1
            cursor += bracket_length
            continue
        if contents.startswith(closing * bracket_length, cursor):
            depth -= 1
            if depth == 0:
                return cursor + bracket_length - 1
            cursor += bracket_length
            continue

        cursor += 1

    error_message = f"Unterminated {'double ' if is_double else ''}bracket `{opening}`"
    raise_parsing_error(contents, start, error_message, length=2 if is_double else 1)


__IDENTIFIER_REGEX = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


def get_identifier(contents: str, start: int) -> tuple[int, str]:
    """Extract a Python identifier starting at index `start`.

    Args:
        contents: Document text.
        start: Index to begin scanning.

    Returns:
        A tuple of (length of identifier match, matched identifier string).
    """
    if start >= len(contents):
        return 0, ""

    m = __IDENTIFIER_REGEX.match(contents, start)
    if not m:
        return 0, ""

    identifier = m.group()
    return len(identifier), identifier


def get_macro(contents: str, start: int) -> tuple[int, str]:
    """Extract a Python macro or parenthesized expression starting at index `start`.

    Can start with either:
      1. A Python identifier (e.g. 'var', 'func(...)', 'obj.attr')
      2. An opening parenthesis (e.g. '(a + b)', '(x * y)[0]')

    Followed by any number of chained attribute lookups ('.attr'),
    subscripts ('[...]'), or call argument groups ('(...)').

    Args:
        contents: Document text.
        start: Index of the first character of the macro name or '('.

    Returns:
        A tuple of (characters consumed, macro expression string).
    """
    if start >= len(contents):
        return 0, ""

    cursor = start
    char = contents[cursor]

    # 1. Base item: either parenthesized expression or base identifier
    if char == "(":
        bracket_end = find_matching_bracket(contents, cursor)
        macro_str = contents[cursor : bracket_end + 1]
        cursor = bracket_end + 1
    else:
        length, identifier = get_identifier(contents, cursor)
        if length == 0:
            return 0, ""
        macro_str = identifier
        cursor += length

    # 2. Chained lookups, calls, and subscripts
    while cursor < len(contents):
        char = contents[cursor]

        if char == ".":
            # Avoid sentence-ending periods or invalid attributes
            if cursor + 1 >= len(contents) or contents[cursor + 1] in (" ", "\t", "\n"):
                break
            attr_len, attr_name = get_identifier(contents, cursor + 1)
            if attr_len == 0:
                break
            cursor += 1 + attr_len
            macro_str += "." + attr_name
            continue

        if char in ("(", "["):
            bracket_end = find_matching_bracket(contents, cursor)
            macro_str += contents[cursor : bracket_end + 1]
            cursor = bracket_end + 1
            continue

        break

    return cursor - start, macro_str


__FORMAT_SPECIFIER_PATTERN = re.compile(
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
    """Extract a Python format specification (e.g. `:.2f`, `:>10`) starting at `start`.

    Args:
        contents: Document text.
        start: Index pointing to the initial ':'.

    Returns:
        A tuple of (length consumed, format string including colon or empty string).
    """
    if start >= len(contents) or contents[start] != ":":
        return 0, ""

    # A colon followed by whitespace or at EOF is an English punctuation mark, not a specifier
    if start + 1 >= len(contents) or contents[start + 1] in (" ", "\t", "\n"):
        return 0, ""

    m = __FORMAT_SPECIFIER_PATTERN.match(contents, start)
    if m is None:
        return 0, ""

    specifier = m.group(0)
    if specifier == ":":
        return 0, ""

    return len(specifier), specifier


# ==============================================================================
# Markdown Formatting Helpers
# ==============================================================================


def clean_macro(macro: str) -> str:
    # check if the macro is a single print statement. If it is, strip the
    # `print` function call

    macro = macro.strip()
    if not macro.startswith("print("):
        return macro

    end_bracket = find_matching_bracket(macro, 5)
    if end_bracket < len(macro) - 1:
        # This is not just a print statement
        return macro

    return macro[6:-1]


def format_as_markdown(
    macro: str,
    is_double: bool,
    is_quiet: bool,
    is_solo: bool = False,
    is_inline: bool | None = None,
    specifier: str | None = None,
) -> str:
    """Format an expression or macro into a Pandoc-annotated code span or block.

    Applies classes:
        - `.py`: Evaluates and inserts stdout text verbatim.
        - `.py-md`: Evaluates and expects a Panflute AST element.
        - `.quiet`: Suppresses document insertion (runs side-effects only).
        - `.inline` / `.block`: Explicit layout hint.

    Args:
        macro: The code string or variable name to execute.
        is_double: True if invoked with '%%' (AST object mode).
        is_quiet: True if terminated with ';' (suppress stdout).
        is_solo: True if directive sits solitary on its line (emits fenced block).
        is_inline: True for forced inline, False for forced block, None for auto.
        specifier: Optional Python format specifier (e.g. '.2f').

    Returns:
        Pandoc Markdown string (e.g. ` `` print(a) ``{.py} `).
    """
    # 1. If not double ('%%') and not quiet, wrap macro in print() or format specifier template
    # 2. Assemble Pandoc class string: '.py-md' if is_double else '.py'
    # 3. Append modifier classes: '.quiet' if is_quiet, '.inline' or '.block' if specified
    # 4. If is_solo is True, format as multiline fenced block: ```{classes}\n{macro}\n```
    # 5. Otherwise, format as inline backticks: `` {macro} ``{classes}
    if not is_double and not is_quiet:
        macro = clean_macro(macro)
        if specifier is not None:
            macro = f"print('{{{specifier}}}'.format({macro}))"
        else:
            macro = f"print({macro})"

    classes = [".py-md" if is_double else ".py"]
    if is_quiet:
        classes.append(".quiet")
    if is_inline is not None:
        classes.append(".inline" if is_inline else ".block")

    classes = " ".join(classes)

    if is_solo:
        return f"\n```{{{classes}}}\n{macro}\n```\n"

    return f"`` {macro} ``{{{classes}}}"


def format_block_as_markdown(
    block: str,
    is_quiet: bool,
    is_solo: bool = False,
) -> str:
    """Format a multi-line Python code block into Pandoc-annotated Markdown.

    Args:
        block: Multi-line Python code string.
        is_quiet: True if terminated with ';'.
        is_solo: True if solitary on its line.

    Returns:
        Pandoc-formatted code block string.
    """
    # 1. Assemble Pandoc class string: '.py' plus '.quiet' if is_quiet is True
    # 2. If is_solo is True, wrap in fenced code block: ```{classes}\n{block}\n```
    # 3. Otherwise, wrap in inline double backticks: `` {block} ``{classes}
    classes = [".py"]

    if is_quiet:
        classes.append(".quiet")

    classes = " ".join(classes)

    if is_solo:
        return f"\n```{{{classes}}}\n{block}\n```\n"
    return f"`` {block} ``{{{classes}}}"


# ==============================================================================
# Directive Handlers
# ==============================================================================


def read_pyndoc_macro(contents: str, start: int) -> tuple[int, str]:
    """Parse inline macros: %var, %%var, %func(...), %%func(...).

    Handles optional 'i'/'b' prefix, chained calls/subscripts, format specifiers,
    and trailing semicolons.

    Args:
        contents: Full document text.
        start: Character index pointing to start of macro directive.

    Returns:
        A tuple of (characters consumed, replacement Markdown text).
    """
    # 1. Check for AST flag ('%%' vs '%')
    # 2. Extract macro expression using get_macro (identifiers, chained calls/subscripts, or parenthesized expressions)
    # 3. Check for format specifier (':fmt') and quiet flag (';')
    # 4. Check if solitary on line with is_only_text_on_line
    # 5. Return (consumed_characters, format_as_markdown(...))

    # Note: No longer supporting `'i'` and `'b'` indicators; they're not
    # necessary anymore
    if start >= len(contents):
        return 0, ""

    if contents[start] != "%":
        return 0, ""

    run_length = scan_delimiter_run(contents, start)

    if run_length > 2:
        # likely a file input, not a macro
        return 0, ""

    is_double = run_length == 2
    cursor = start + run_length

    length, macro = get_macro(contents, cursor)
    if length == 0:
        # misidentified
        return 0, ""

    cursor += length

    specifier = None
    if cursor < len(contents) and contents[cursor] == ":":
        specifier_length, spec = get_format_specifier(contents, cursor)
        if specifier_length > 0:
            cursor += specifier_length
            specifier = spec

    is_quiet = False
    if cursor < len(contents) and contents[cursor] == ";":
        cursor += 1
        is_quiet = True

    is_solo = is_only_text_on_line(contents, start, cursor)

    return cursor - start, format_as_markdown(
        macro,
        is_double=is_double,
        is_quiet=is_quiet,
        is_solo=is_solo,
        is_inline=None,
        specifier=specifier,
    )


def read_pyndoc_expression(contents: str, start: int) -> tuple[int, str]:
    """Parse parenthesized expression macros: %(a == b), %%(a + b).

    Unified with read_pyndoc_macro.
    """
    return read_pyndoc_macro(contents, start)


def read_pyndoc_block(contents: str, start: int) -> tuple[int, str]:
    """Parse embedded Python execution blocks: %{ code } or %%{ code }.

    Args:
        contents: Document text.
        start: Character index of '%{'.

    Returns:
        A tuple of (characters consumed, replacement Markdown text).
    """
    # 1. Find closing bracket of block using find_matching_bracket
    # 2. Extract inner code, strip outer newlines, and normalize indentation with deindent()
    # 3. Check for trailing quiet flag (';')
    # 4. Check if solitary on line with is_only_text_on_line
    # 5. Return (consumed_characters, format_block_as_markdown(...))
    if start >= len(contents):
        return 0, ""

    if contents[start] != "%":
        return 0, ""

    run_length = scan_delimiter_run(contents, start)

    if run_length > 2:
        # likely a file input, not a macro
        return 0, ""

    is_double = run_length == 2
    cursor = start + run_length

    bracket_end = find_matching_bracket(contents, cursor)
    # removing the outer braces
    block = contents[cursor + 1 : bracket_end]
    block = block.strip("\n")
    block = deindent(block)
    is_quiet = bracket_end + 1 < len(contents) and contents[bracket_end + 1] == ";"
    cursor = bracket_end + (2 if is_quiet else 1)
    is_solo = is_only_text_on_line(contents, start, cursor)
    return cursor - start, format_block_as_markdown(
        block, is_quiet=is_quiet, is_solo=is_solo
    )


def read_pyndoc_file(
    contents: str,
    start: int,
    target_format: str | None = None,
) -> tuple[int, str]:
    """Parse external Python file execution directives: %%%py{path.py}.

    Args:
        contents: Document text.
        start: Character index of '%%%py{'.
        target_format: Optional Pandoc target format string for path interpolation.

    Returns:
        A tuple of (characters consumed, replacement Markdown text).
    """
    # 1. Find closing bracket of '%%%py{...}' using find_matching_bracket
    # 2. Extract filename path and substitute '{format}' with target_format
    # 3. Check for quiet flag (';') and solitary line placement
    # 4. Format as inline backticks or fenced block with class '.py-file'
    # 5. Return (consumed_characters, formatted_markdown)
    if start >= len(contents):
        return 0, ""

    if contents[start] != "%":
        return 0, ""

    run_length = scan_delimiter_run(contents, start)

    if run_length != 3:
        # not a file input
        return 0, ""

    cursor = start + run_length

    file_type = None
    m = re.match(r"[^\{]*", contents[cursor:])
    if m is None:
        return 0, ""

    file_type = m.group()
    length = len(file_type)
    cursor += length

    block_start = cursor + 1
    block_end = find_matching_bracket(contents, cursor)
    block = contents[block_start:block_end].strip()
    cursor = block_end + 1

    is_quiet = False
    if cursor < len(contents) and contents[cursor] == ";":
        cursor += 1
        is_quiet = True

    formatted_block = None

    match file_type:
        case "py":
            formatted_block = include_py_file(
                block,
                contents,
                block_start,
                block_end,
                target_format,
                is_quiet=is_quiet,
            )
        case "md":
            formatted_block = include_md_file(
                block,
                contents,
                block_start,
                block_end,
                target_format,
                is_quiet=is_quiet,
            )
        case "mdifformat":
            formatted_block = include_md_conditional_file(
                block,
                contents,
                block_start,
                block_end,
                target_format,
                is_quiet=is_quiet,
            )
        case _:
            raise_parsing_error(
                contents,
                start + 3,
                "Unrecognised file directive",
                length=len(file_type),
            )

    return cursor - start, formatted_block


def include_py_file(
    filename: str,
    contents: str,
    start: int,
    end: int,
    target_format: str | None = None,
    is_quiet: bool = False,
) -> str:
    # Contents, start and end for error reporting only
    target_fmt = target_format or ""
    filename = filename.replace("{format}", target_fmt)
    filepath = Path(filename)
    if not filepath.exists():
        raise_parsing_error(
            contents,
            start,
            "Python file does not exist",
            end - start,
            FileNotFoundError,
        )
    if not filepath.is_file():
        raise_parsing_error(
            contents,
            start,
            "Filepath exists but is not a file",
            end - start,
            FileNotFoundError,
        )

    classes = [".py-file"]
    if is_quiet:
        classes.append(".quiet")

    classes = " ".join(classes)

    return f"`` {filepath.absolute()} ``{{{classes}}}"


def include_md_file(
    filename: str,
    contents: str,
    start: int,
    end: int,
    target_format: str | None = None,
    is_quiet: bool = False,
) -> str:
    """Read, preprocess, and return the contents of an included Markdown file.

    Args:
        filename: Relative or absolute path to the Markdown file.
        contents: Parent document text (for error reporting).
        start: Starting character index of the file block in parent document.
        end: Ending character index of the file block in parent document.
        target_format: The target format passed to Pandoc.
        is_quiet: If True, suppresses output (returns empty string).

    Returns:
        Preprocessed Markdown text from the included file.
    """
    target_fmt = target_format or ""
    filename = filename.strip().replace("{format}", target_fmt)
    filepath = Path(filename)

    if not filepath.exists():
        raise_parsing_error(
            contents,
            start,
            f"Markdown file does not exist: '{filename}'",
            end - start,
            FileNotFoundError,
        )
    if not filepath.is_file():
        raise_parsing_error(
            contents,
            start,
            f"Filepath exists but is not a file: '{filename}'",
            end - start,
            FileNotFoundError,
        )

    with filepath.open("r", encoding="utf-8") as f:
        file_contents = f.read()

    file_contents = preprocess(file_contents, target_format)
    return "" if is_quiet else file_contents


def include_md_conditional_file(
    filename: str,
    contents: str,
    start: int,
    end: int,
    target_format: str | None = None,
    is_quiet: bool = False,
) -> str:
    """Conditionally include and preprocess a Markdown file based on target format.

    The block consists of semicolon-separated clauses in the format:
        fmt1, fmt2: path/to/file1.md;
        fmt3: path/to/file2.md;

    Args:
        filename: Semicolon-separated format options block.
        contents: Parent document text (for error reporting).
        start: Starting character index of the block in parent document.
        end: Ending character index of the block in parent document.
        target_format: The target format passed to Pandoc.
        is_quiet: If True, suppresses output (returns empty string).

    Returns:
        Preprocessed Markdown text if a matching format is found, else empty string.
    """
    target = (target_format or "").strip().lower()

    # Semicolon-delimited options: "html, latex: file1.md; epub: file2.md"
    raw_options = [opt.strip() for opt in filename.split(";") if opt.strip()]

    for option in raw_options:
        if ":" not in option:
            raise_parsing_error(
                contents,
                start,
                f"Invalid conditional format specification '{option}'. Expected 'format: path'",
                end - start,
            )

        formats_part, path_part = option.split(":", 1)
        formats = [fmt.strip().lower() for fmt in formats_part.split(",") if fmt.strip()]
        file_path_str = path_part.strip()

        if target in formats:
            return include_md_file(
                file_path_str,
                contents,
                start,
                end,
                target_format,
                is_quiet=is_quiet,
            )

    return ""


# ==============================================================================
# Main Pipeline Entry Point
# ==============================================================================

__TRIGGER_RE = re.compile(r"[%`~\$\\]|<!--")


def preprocess(
    contents: str,
    target_format: str | None = None,
    console: Console | None = None,
) -> str:
    """Preprocess a Markdown document, transforming Pyndoc directives into Pandoc syntax.

    This is the primary public entry point for the preprocessor. It scans through
    the document text, skipping Markdown comments, code spans, and math delimiters,
    while replacing Pyndoc macros, execution blocks, and file inclusions.

    Args:
        contents: Raw Markdown document text.
        target_format: The target format passed to Pandoc (e.g. 'html', 'latex', 'pdf').
        console: Optional Rich Console. If provided, sets the module console. If None
            and no module console has been initialised, creates a default terminal Console.

    Returns:
        Preprocessed Markdown text ready for Pandoc AST conversion.
    """
    global _CONSOLE
    if console is not None:
        _CONSOLE = console
    elif _CONSOLE is None:
        _CONSOLE = Console()

    output = io.StringIO()
    cursor = 0
    total_len = len(contents)

    while cursor < total_len:
        match = __TRIGGER_RE.search(contents, cursor)
        if not match:
            output.write(contents[cursor:])
            break

        trigger_pos = match.start()
        if trigger_pos > cursor:
            output.write(contents[cursor:trigger_pos])
            cursor = trigger_pos

        char = contents[cursor]

        # 1. HTML Comments (stripped from output)
        if char == "<":
            consumed, _ = read_comment_span(contents, cursor)
            if consumed > 0:
                cursor += consumed
                continue
            output.write(char)
            cursor += 1
            continue

        # 2. Escaped characters and bracket math
        if char == "\\":
            consumed, math_text = read_bracket_math_span(contents, cursor)
            if consumed > 0:
                output.write(math_text)
                cursor += consumed
                continue

            if cursor + 1 < total_len:
                output.write(contents[cursor : cursor + 2])
                cursor += 2
            else:
                output.write(char)
                cursor += 1
            continue

        # 3. Markdown code spans & fenced blocks
        if char in ("`", "~"):
            consumed, code_text = read_code_span(contents, cursor)
            if consumed > 0:
                output.write(code_text)
                cursor += consumed
                continue
            output.write(char)
            cursor += 1
            continue

        # 4. Math spans ($...$ or $$...$$)
        if char == "$":
            consumed, math_text = read_dollar_math_span(contents, cursor)
            if consumed > 0:
                output.write(math_text)
                cursor += consumed
                continue
            output.write(char)
            cursor += 1
            continue

        # 5. Pyndoc directives (%)
        if char == "%":
            run_length = scan_delimiter_run(contents, cursor)
            if run_length == 3:
                consumed, rep = read_pyndoc_file(contents, cursor, target_format)
                if consumed > 0:
                    output.write(rep)
                    cursor += consumed
                    continue
            elif run_length in (1, 2):
                after_percent = cursor + run_length
                if after_percent < total_len and contents[after_percent] == "{":
                    consumed, rep = read_pyndoc_block(contents, cursor)
                    if consumed > 0:
                        output.write(rep)
                        cursor += consumed
                        continue
                else:
                    consumed, rep = read_pyndoc_macro(contents, cursor)
                    if consumed > 0:
                        output.write(rep)
                        cursor += consumed
                        continue

            output.write(char)
            cursor += 1
            continue

        output.write(char)
        cursor += 1

    result = output.getvalue()
    return re.sub(r"\n{3,}", "\n\n", result)
