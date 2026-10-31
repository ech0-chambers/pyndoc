"""Unit tests for the Pyndoc preprocessor module (src/pyndoc/preprocess.py)."""

from pathlib import Path
import pytest

from pyndoc.preprocess import (
    # Diagnostics & errors
    PreprocessorError,
    PreprocessorParsingError,
    PreprocessingIndentationError,
    PreprocessingMixedTabsAndSpacesError,
    get_line_number,
    raise_parsing_error,
    _format_windowed_line,
    get_console,
    set_console,
    reset_console,
    no_console,
    # Indentation & formatting
    deindent,
    clean_macro,
    is_only_text_on_line,
    format_as_markdown,
    format_block_as_markdown,
    # Delimiters & island extractors
    scan_delimiter_run,
    read_code_span,
    read_dollar_math_span,
    read_bracket_math_span,
    read_string_span,
    read_comment_span,
    find_matching_bracket,
    # Identifiers & macro scanning
    get_identifier,
    get_macro,
    get_format_specifier,
    # Directives
    read_pyndoc_macro,
    read_pyndoc_expression,
    read_pyndoc_block,
    read_pyndoc_file,
    include_md_dir,
    # Pipeline
    preprocess,
)


# ==============================================================================
# Diagnostics & Error Formatting Tests
# ==============================================================================


class TestDiagnostics:
    def test_get_line_number(self):
        text = "line 0\nline 1\nline 2"
        assert get_line_number(text, 0) == 0
        assert get_line_number(text, 5) == 0
        assert get_line_number(text, 7) == 1
        assert get_line_number(text, 14) == 2

    def test_raise_parsing_error_first_line(self):
        text = "%invalid_directive"
        with pytest.raises(PreprocessorParsingError) as exc_info:
            raise_parsing_error(text, 0, "Invalid directive syntax", length=1)
        err = str(exc_info.value)
        assert "Preprocessor parsing error at line 1" in err
        assert "^" in err

    def test_raise_parsing_error_middle_line(self):
        text = "first line\nsecond line\nerror %here\nfourth line"
        start = text.index("%here")
        with pytest.raises(PreprocessorParsingError) as exc_info:
            raise_parsing_error(text, start, "Something went wrong", length=5)
        err = str(exc_info.value)
        assert "Preprocessor parsing error at line 3" in err
        assert "^^^^^" in err

    def test_format_windowed_line_short(self):
        line = "let x = %foo(1, 2)"
        win_line, carets = _format_windowed_line(line, col=8, length=4, max_width=80)
        assert win_line == line
        assert carets == " " * 8 + "^^^^"

    def test_format_windowed_line_right_truncated(self):
        line = "x = %err(" + "a" * 100 + ")"
        win_line, carets = _format_windowed_line(line, col=4, length=4, max_width=40)
        assert len(win_line) <= 40
        assert win_line.endswith("...")
        assert not win_line.startswith("...")
        assert "^^^^" in carets
        caret_pos = carets.index("^")
        assert win_line[caret_pos : caret_pos + 4] == "%err"

    def test_format_windowed_line_left_truncated(self):
        line = "x = " + "a" * 100 + " + %bad"
        col = line.index("%bad")
        win_line, carets = _format_windowed_line(line, col=col, length=4, max_width=40)
        assert len(win_line) <= 40
        assert win_line.startswith("...")
        assert not win_line.endswith("...")
        assert "^^^^" in carets
        caret_pos = carets.index("^")
        assert win_line[caret_pos : caret_pos + 4] == "%bad"

    def test_format_windowed_line_both_truncated(self):
        line = "a" * 50 + " + %bad + " + "b" * 50
        col = line.index("%bad")
        win_line, carets = _format_windowed_line(line, col=col, length=4, max_width=40)
        assert len(win_line) <= 40
        assert win_line.startswith("...")
        assert win_line.endswith("...")
        assert "^^^^" in carets
        caret_pos = carets.index("^")
        assert win_line[caret_pos : caret_pos + 4] == "%bad"

    def test_format_windowed_line_oversized_token(self):
        line = "prefix " + "X" * 60 + " suffix"
        win_line, carets = _format_windowed_line(line, col=7, length=60, max_width=40)
        assert len(win_line) <= 40
        assert "^" in carets
        assert len(carets) <= 40

    def test_raise_parsing_error_long_line_never_wraps(self, monkeypatch):
        # Force terminal width to 50 columns
        monkeypatch.setattr("shutil.get_terminal_size", lambda fallback: (50, 24))
        long_line = "start " + "a" * 80 + " %bad_macro " + "b" * 80 + " end"
        start = long_line.index("%bad_macro")
        with pytest.raises(PreprocessorParsingError) as exc_info:
            raise_parsing_error(long_line, start, "Invalid macro", length=len("%bad_macro"))
        err = str(exc_info.value)
        for line in err.splitlines():
            if line.startswith(">   "):
                assert len(line) <= 50, f"Line wrapped beyond terminal width: {line}"


# ==============================================================================
# Console Management Tests
# ==============================================================================


class TestConsoleManagement:
    def setup_method(self):
        reset_console()

    def teardown_method(self):
        reset_console()

    def test_no_console_redirects_to_string_buffer(self):
        buffer_console = no_console()
        assert get_console() is buffer_console

        # Calling preprocess should NOT overwrite buffer_console
        doc = "Value is %var."
        res = preprocess(doc)
        assert get_console() is buffer_console
        assert "`` print(var) ``{.py}." in res

    def test_no_console_captures_rich_error_output(self):
        buf_console = no_console()
        doc = "%{ unclosed block"
        with pytest.raises(PreprocessorParsingError):
            preprocess(doc)

        buf_console.file.seek(0)
        output = buf_console.file.getvalue()
        assert "Preprocessor parsing error" in output

    def test_preprocess_initialises_default_console(self):
        assert get_console() is None
        preprocess("# Hello")
        assert get_console() is not None

    def test_preprocess_custom_console_parameter(self):
        from rich.console import Console
        import io

        custom_buf = io.StringIO()
        custom_console = Console(file=custom_buf)

        preprocess("# Test", console=custom_console)
        assert get_console() is custom_console


# ==============================================================================
# Indentation & Formatting Tests
# ==============================================================================


class TestIndentationAndFormatting:
    def test_deindent_standard(self):
        code = "    def foo():\n        x = 1\n        return x"
        expected = "def foo():\n    x = 1\n    return x"
        assert deindent(code) == expected

    def test_deindent_empty_or_whitespace(self):
        assert deindent("") == ""
        assert deindent("    \n\n   \n") == ""

    def test_deindent_mixed_tabs_spaces_same_line(self):
        with pytest.raises(PreprocessingMixedTabsAndSpacesError):
            deindent(" \tdef foo():\n    pass")

    def test_deindent_mixed_tabs_spaces_different_lines(self):
        with pytest.raises(PreprocessingMixedTabsAndSpacesError):
            deindent("\tdef foo():\n    pass")

    def test_deindent_inconsistent_indentation(self):
        code = "    def foo():\n  x = 1"
        with pytest.raises(PreprocessingIndentationError):
            deindent(code)

    def test_clean_macro(self):
        assert clean_macro("print(x)") == "x"
        assert clean_macro("print(foo.bar(1, 2))") == "foo.bar(1, 2)"
        assert clean_macro("print(x) + 1") == "print(x) + 1"
        assert clean_macro("foo") == "foo"

    def test_is_only_text_on_line(self):
        doc = "Intro\n  %macro  \nOutro"
        start = doc.index("%macro")
        end = start + len("%macro")
        assert is_only_text_on_line(doc, start, end) is True

        doc_inline = "Some words %macro other words"
        start_inline = doc_inline.index("%macro")
        end_inline = start_inline + len("%macro")
        assert is_only_text_on_line(doc_inline, start_inline, end_inline) is False

    def test_format_as_markdown(self):
        # Single percent default -> wraps with print() and .py
        assert format_as_markdown("var", is_double=False, is_quiet=False) == "`` print(var) ``{.py}"
        # Single percent with format specifier
        res_fmt = format_as_markdown("var", is_double=False, is_quiet=False, specifier=":.2f")
        assert res_fmt == "`` print('{:.2f}'.format(var)) ``{.py}"
        # Double percent AST object mode -> no print(), .py-md
        assert format_as_markdown("var", is_double=True, is_quiet=False) == "`` var ``{.py-md}"
        # Quiet flag
        assert format_as_markdown("var", is_double=False, is_quiet=True) == "`` var ``{.py .quiet}"
        # Solitary fenced block
        res_solo = format_as_markdown("var", is_double=False, is_quiet=False, is_solo=True)
        assert res_solo == "\n```{.py}\nprint(var)\n```\n"

    def test_format_block_as_markdown(self):
        block = "x = 1\ny = 2"
        res_inline = format_block_as_markdown(block, is_quiet=False, is_solo=False)
        assert res_inline == f"`` {block} ``{{.py}}"

        res_solo = format_block_as_markdown(block, is_quiet=True, is_solo=True)
        assert res_solo == f"\n```{{.py .quiet}}\n{block}\n```\n"


# ==============================================================================
# Delimiters & Island Extractors Tests
# ==============================================================================


class TestIslandExtractors:
    def test_scan_delimiter_run(self):
        assert scan_delimiter_run("```code", 0) == 3
        assert scan_delimiter_run("$$math", 0) == 2
        assert scan_delimiter_run("~strike", 0) == 1
        assert scan_delimiter_run("", 0) == 0
        assert scan_delimiter_run("abc", 5) == 0

    def test_read_code_span_inline(self):
        doc = "Here is `code` text"
        consumed, text = read_code_span(doc, 8)
        assert consumed == 6
        assert text == "`code`"

    def test_read_code_span_double_backtick(self):
        doc = "Here is ``code `with` backtick`` text"
        consumed, text = read_code_span(doc, 8)
        assert consumed == 24
        assert text == "``code `with` backtick``"

    def test_read_code_span_fenced(self):
        doc = "```python\nprint(1)\n```\nRest"
        consumed, text = read_code_span(doc, 0)
        assert consumed == len("```python\nprint(1)\n```")
        assert text == "```python\nprint(1)\n```"

    def test_read_code_span_tilde(self):
        doc = "~~~python\nprint(2)\n~~~"
        consumed, text = read_code_span(doc, 0)
        assert consumed == len(doc)
        assert text == doc

    def test_read_code_span_single_tilde_ignored(self):
        # Single and double tildes are strikethrough in markdown, not code
        assert read_code_span("~strike~", 0) == (0, "")
        assert read_code_span("~~strike~~", 0) == (0, "")

    def test_read_code_span_unterminated_raises(self):
        with pytest.raises(PreprocessorParsingError):
            read_code_span("```python\ncode without closing fence", 0)

    def test_read_dollar_math_span_inline(self):
        doc = "Formula $x^2 + y^2 = z^2$ end"
        consumed, text = read_dollar_math_span(doc, 8)
        assert consumed == len("$x^2 + y^2 = z^2$")
        assert text == "$x^2 + y^2 = z^2$"

    def test_read_dollar_math_span_display(self):
        doc = "$$\\int_0^1 f(x) dx$$"
        consumed, text = read_dollar_math_span(doc, 0)
        assert consumed == len(doc)
        assert text == doc

    def test_read_dollar_math_span_currency_false_positives(self):
        # Solitary $ followed by space
        assert read_dollar_math_span("$ 50 is cost", 0) == (0, "")
        # Solitary $ followed by digits in prose with subsequent currency
        doc = "I have $5 in pocket and $10 in bank."
        start1 = doc.index("$5")
        assert read_dollar_math_span(doc, start1) == (0, "")
        start2 = doc.index("$10")
        assert read_dollar_math_span(doc, start2) == (0, "")

    def test_read_bracket_math_span(self):
        inline_doc = r"\(a + b\) text"
        consumed, text = read_bracket_math_span(inline_doc, 0)
        assert consumed == 9
        assert text == r"\(a + b\)"

        display_doc = r"\[\sum_{i=1}^n x_i\] text"
        consumed, text = read_bracket_math_span(display_doc, 0)
        assert consumed == 20
        assert text == r"\[\sum_{i=1}^n x_i\]"

        # Non-bracket escapes
        assert read_bracket_math_span(r"\alpha", 0) == (0, "")

    def test_read_string_span(self):
        assert read_string_span("'hello'", 0) == (7, "'hello'")
        assert read_string_span('"hello \\"world\\""', 0) == (17, '"hello \\"world\\""')
        assert read_string_span("'''multiline\ntext'''", 0) == (20, "'''multiline\ntext'''")
        assert read_string_span('"""multiline\ntext"""', 0) == (20, '"""multiline\ntext"""')

    def test_read_comment_span(self):
        comment = "<!-- This is a comment -->"
        assert read_comment_span(comment, 0) == (len(comment), comment)
        assert read_comment_span("<div>", 0) == (0, "")

    def test_find_matching_bracket(self):
        assert find_matching_bracket("func(1, (2 + 3))", 4) == 15
        # Skips strings with brackets inside
        assert find_matching_bracket('func(")", 1)', 4) == 11
        # Skips comments with brackets inside
        assert find_matching_bracket("func(x, # unmatched )\n y)", 4) == 24
        # Double brackets (last character at index 16)
        assert find_matching_bracket("{{ raw { arg } }}", 0, is_double=True) == 16
        with pytest.raises(PreprocessorParsingError):
            find_matching_bracket("func(unclosed", 4)


# ==============================================================================
# Identifier & Macro Scanning Tests
# ==============================================================================


class TestMacroScanning:
    def test_get_identifier(self):
        assert get_identifier("my_var = 1", 0) == (6, "my_var")
        assert get_identifier("_hidden_var", 0) == (11, "_hidden_var")
        assert get_identifier("123invalid", 0) == (0, "")
        assert get_identifier("%var", 0) == (0, "")

    def test_get_macro_simple_variable(self):
        assert get_macro("var", 0) == (3, "var")

    def test_get_macro_chained_attributes(self):
        assert get_macro("user.profile.name", 0) == (17, "user.profile.name")

    def test_get_macro_function_calls_and_indices(self):
        assert get_macro("calc(1, 2)", 0) == (10, "calc(1, 2)")
        assert get_macro("data[0].item()", 0) == (14, "data[0].item()")

    def test_get_macro_parenthesized_expressions(self):
        assert get_macro("(a + b)", 0) == (7, "(a + b)")
        assert get_macro("(x * 2)[0]", 0) == (10, "(x * 2)[0]")
        assert get_macro("(a + b).real", 0) == (12, "(a + b).real")

    def test_get_macro_sentence_period_protection(self):
        doc = "user.name. Next sentence"
        consumed, macro = get_macro(doc, 0)
        assert consumed == 9
        assert macro == "user.name"

    def test_get_format_specifier(self):
        assert get_format_specifier(":.2f", 0) == (4, ":.2f")
        assert get_format_specifier(":>10", 0) == (4, ":>10")
        assert get_format_specifier(":*^10s", 0) == (6, ":*^10s")
        assert get_format_specifier(":10d", 0) == (4, ":10d")
        # False positives
        assert get_format_specifier(":", 0) == (0, "")
        assert get_format_specifier(": solitary colon", 0) == (0, "")
        assert get_format_specifier(": fruit", 0) == (0, "")


# ==============================================================================
# Directive Handlers Tests
# ==============================================================================


class TestDirectives:
    def test_read_pyndoc_macro_variable(self):
        doc = "Result: %my_var."
        consumed, out = read_pyndoc_macro(doc, 8)
        assert consumed == 7
        assert out == "`` print(my_var) ``{.py}"

    def test_read_pyndoc_macro_ast_mode(self):
        doc = "Object: %%my_obj."
        consumed, out = read_pyndoc_macro(doc, 8)
        assert consumed == 8
        assert out == "`` my_obj ``{.py-md}"

    def test_read_pyndoc_macro_with_format_specifier(self):
        doc = "Value: %price:.2f."
        consumed, out = read_pyndoc_macro(doc, 7)
        assert consumed == 10
        assert out == "`` print('{:.2f}'.format(price)) ``{.py}"

    def test_read_pyndoc_macro_quiet(self):
        doc = "Run: %init_db();"
        consumed, out = read_pyndoc_macro(doc, 5)
        assert consumed == 11
        assert out == "`` init_db() ``{.py .quiet}"

    def test_read_pyndoc_expression(self):
        doc = "Calc: %(a + b * 2)."
        consumed, out = read_pyndoc_expression(doc, 6)
        assert consumed == 12
        assert out == "`` print((a + b * 2)) ``{.py}"

    def test_read_pyndoc_block(self):
        doc = "%{\nx = 10\ny = 20\n}"
        consumed, out = read_pyndoc_block(doc, 0)
        assert consumed == len(doc)
        assert "\n```{.py}\nx = 10\ny = 20\n```\n" in out

    def test_include_py_file(self, tmp_path):
        script = tmp_path / "script.py"
        script.write_text("x = 42\n")

        doc = f"%%%py{{{script}}}"
        consumed, out = read_pyndoc_file(doc, 0)
        assert consumed == len(doc)
        assert f"`` {script.resolve()} ``{{.py-file}}" == out

    def test_include_md_file(self, tmp_path):
        sub_md = tmp_path / "section.md"
        sub_md.write_text("# Chapter\nInline %my_var here")

        doc = f"%%%md{{{sub_md}}}"
        consumed, out = read_pyndoc_file(doc, 0)
        assert consumed == len(doc)
        assert "# Chapter" in out
        assert "`` print(my_var) ``{.py}" in out

    def test_include_md_dir_ordering_and_filtering(self, tmp_path):
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "02_second.md").write_text("Second chapter: %val2.")
        (chapters_dir / "01_first.md").write_text("First chapter: %val1.")
        (chapters_dir / "notes.txt").write_text("Do not include this")

        doc = f"%%%mddir{{{chapters_dir}}}"
        consumed, out = read_pyndoc_file(doc, 0)
        assert consumed == len(doc)

        # Verify filename order: 01_first before 02_second
        idx_first = out.find("First chapter:")
        idx_second = out.find("Second chapter:")
        assert idx_first != -1
        assert idx_second != -1
        assert idx_first < idx_second

        # Verify preprocessing occurred
        assert "`` print(val1) ``{.py}" in out
        assert "`` print(val2) ``{.py}" in out

        # Verify non-markdown file was ignored
        assert "Do not include this" not in out

    def test_include_md_dir_quiet(self, tmp_path):
        chapters_dir = tmp_path / "quiet_chapters"
        chapters_dir.mkdir()
        (chapters_dir / "a.md").write_text("A content")

        doc = f"%%%mddir{{{chapters_dir}}};"
        consumed, out = read_pyndoc_file(doc, 0)
        assert consumed == len(doc)
        assert out == ""

    def test_include_md_dir_nonexistent(self, tmp_path):
        fake_dir = tmp_path / "nonexistent_dir"
        doc = f"%%%mddir{{{fake_dir}}}"
        with pytest.raises(FileNotFoundError) as exc_info:
            read_pyndoc_file(doc, 0)
        assert "Markdown directory does not exist" in str(exc_info.value)

    def test_include_md_dir_not_a_directory(self, tmp_path):
        a_file = tmp_path / "some_file.md"
        a_file.write_text("File content")
        doc = f"%%%mddir{{{a_file}}}"
        with pytest.raises(NotADirectoryError) as exc_info:
            read_pyndoc_file(doc, 0)
        assert "not a directory" in str(exc_info.value)

    def test_include_md_dir_full_pipeline(self, tmp_path):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "part1.md").write_text("Part 1: %x.")
        (docs_dir / "part2.markdown").write_text("Part 2: %y.")

        main_doc = f"# Title\n\n%%%mddir{{{docs_dir}}}\n\n# Conclusion"
        processed = preprocess(main_doc)
        assert "# Title" in processed
        assert "Part 1: `` print(x) ``{.py}." in processed
        assert "Part 2: `` print(y) ``{.py}." in processed
        assert "# Conclusion" in processed

    def test_include_md_dir_direct(self, tmp_path):
        d = tmp_path / "direct_dir"
        d.mkdir()
        (d / "02.md").write_text("Second")
        (d / "01.md").write_text("First")
        res = include_md_dir(str(d), "", 0, 0)
        assert res == "First\n\nSecond"

    def test_include_md_conditional_file(self, tmp_path):
        html_file = tmp_path / "html_content.md"
        html_file.write_text("Only in HTML")
        pdf_file = tmp_path / "pdf_content.md"
        pdf_file.write_text("Only in PDF")

        doc = f"%%%mdifformat{{html: {html_file}; pdf: {pdf_file};}}"

        # When target is HTML
        _, out_html = read_pyndoc_file(doc, 0, target_format="html")
        assert "Only in HTML" in out_html

        # When target is PDF
        _, out_pdf = read_pyndoc_file(doc, 0, target_format="pdf")
        assert "Only in PDF" in out_pdf

        # When target is EPUB (no match)
        _, out_epub = read_pyndoc_file(doc, 0, target_format="epub")
        assert out_epub == ""


# ==============================================================================
# Full Pipeline (preprocess) Tests
# ==============================================================================


class TestPreprocessPipeline:
    def test_preprocess_untouched_areas(self):
        doc = """# Document

Inline code with macro: `%my_var` should be untouched.
Math with percent: $50% discount$ should be untouched.
Currency: I have $5 in pocket and $10 in bank.
Escaped: \\%escaped.
<!-- Comment with %ignored_var -->
"""
        result = preprocess(doc, "html")
        assert "`%my_var`" in result
        assert "$50% discount$" in result
        assert "$5 in pocket and $10 in bank." in result
        assert r"\%escaped." in result
        assert "<!--" not in result  # Comments stripped

    def test_preprocess_complete_document(self):
        doc = """# Test Doc

The value is %data.price:.2f.
Expression is %(a + b).

%{
x = 100
}
"""
        result = preprocess(doc, "html")
        assert "`` print('{:.2f}'.format(data.price)) ``{.py}." in result
        assert "`` print((a + b)) ``{.py}." in result
        assert "```{.py}\nx = 100\n```" in result

    def test_preprocess_double_block_emits_py_md(self):
        # Solitary block with '%%{' should emit .py-md
        doc_solo = "%%{\nimport pyndoc.markdown as md\ntable = md.table([['a', 'b']])\n}"
        result_solo = preprocess(doc_solo, "html")
        assert "```{.py-md}" in result_solo

        # Inline block with '%%{' should emit .py-md
        doc_inline = "Before %%{x = 1} After"
        result_inline = preprocess(doc_inline, "html")
        assert "`` x = 1 ``{.py-md}" in result_inline

        # Quiet double block with semicolon
        doc_quiet = "%%{\nx = 2\n};"
        result_quiet = preprocess(doc_quiet, "html")
        assert "```{.py-md .quiet}" in result_quiet

    def test_preprocess_math_example_integration(self):
        math_file = Path("docs/examples/math_example.md")
        if math_file.exists():
            text = math_file.read_text(encoding="utf-8")
            result = preprocess(text, "html")
            assert "# Sample Assignment" in result
            assert "`` m() ``{.py-md}" in result
            assert "<!--" not in result
