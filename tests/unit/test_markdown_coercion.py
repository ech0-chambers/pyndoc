"""Unit tests for pyndoc.markdown.coercion."""

import panflute as pf
import pytest

import pyndoc.latex as tex
import pyndoc.markdown as md
from pyndoc.formats import Format
from pyndoc.markdown.coercion import (
    PanfluteError,
    PanfluteTypeError,
    PanfluteValueError,
    as_blocks,
    as_cells,
    as_inlines,
    as_plain_or_para,
    clean_attributes,
    clean_classes,
    clean_identifier,
    ensure_block,
    ensure_inline,
    line_break,
    math_display,
    math_inline,
    para,
    plain,
    raw_block,
    raw_inline,
    soft_break,
    space,
    string,
    tokenize_text,
)


class TestDiagnosticsAndExceptions:
    """Verify diagnostic error reporting in PanfluteTypeError and PanfluteValueError."""

    def test_panflute_type_error_subclasses(self):
        err = PanfluteTypeError(expected="Inline", received=pf.Para(), container="bold")
        assert isinstance(err, TypeError)
        assert isinstance(err, PanfluteError)

    def test_block_inside_inline_diagnostic(self):
        para_elem = pf.Para(pf.Str("nested"))
        err = PanfluteTypeError(
            expected="Inline element, string, or number",
            received=para_elem,
            container="bold",
        )
        msg = str(err)
        assert "[bold]" in msg
        assert "Invalid element type: expected Inline element, string, or number" in msg
        assert "received 'Para'" in msg
        assert "Problem:" in msg
        assert "Panflute does not permit Block elements ('Para') to be nested inside Inline elements." in msg
        assert "Solution:" in msg
        assert "Change: md.bold(md.paragraph(...))" in msg
        assert "To:     md.paragraph(md.bold(...))" in msg

    def test_inline_inside_block_diagnostic(self):
        str_elem = pf.Str("inline_text")
        err = PanfluteTypeError(
            expected="Block element",
            received=str_elem,
            container="block_quote",
        )
        msg = str(err)
        assert "[block_quote]" in msg
        assert "Container 'block_quote' requires Block-level elements" in msg
        assert "md.paragraph(Str(inline_text))" in msg

    def test_dict_diagnostic(self):
        bad_dict = {"a": 1}
        err = PanfluteTypeError(
            expected="Inline element",
            received=bad_dict,
            container="bold",
        )
        msg = str(err)
        assert "Dictionaries cannot be directly inserted" in msg
        assert "md.table(dict_data)" in msg

    def test_custom_problem_and_solution_override(self):
        err = PanfluteTypeError(
            expected="CustomType",
            received=42,
            container="custom_func",
            problem="Special invariant failed.",
            solution="Do this specific thing instead.",
        )
        msg = str(err)
        assert "Problem:  Special invariant failed." in msg
        assert "Solution: Do this specific thing instead." in msg

    def test_panflute_value_error_subclasses_and_matching(self):
        err = PanfluteValueError(
            parameter="alignment",
            received="centr",
            valid_options=["left", "center", "right", "default"],
            container="table",
        )
        assert isinstance(err, ValueError)
        assert isinstance(err, PanfluteError)
        msg = str(err)
        assert "[table]" in msg
        assert "Invalid value for parameter 'alignment': 'centr'." in msg
        assert "Valid options are: 'left', 'center', 'right', 'default'." in msg
        assert "Did you mean: 'center'?" in msg

    def test_long_repr_truncation_in_type_error(self):
        long_val = "x" * 200
        err = PanfluteTypeError(expected="Inline", received=long_val, container="test")
        assert "..." in str(err)


class TestTextTokenization:
    """Verify conversion of raw strings into Pandoc AST inline nodes."""

    def test_empty_string(self):
        assert tokenize_text("") == []

    def test_single_word(self):
        tokens = tokenize_text("Pyndoc")
        assert len(tokens) == 1
        assert isinstance(tokens[0], pf.Str)
        assert tokens[0].text == "Pyndoc"

    def test_words_and_spaces(self):
        tokens = tokenize_text("Hello world")
        assert len(tokens) == 3
        assert isinstance(tokens[0], pf.Str) and tokens[0].text == "Hello"
        assert isinstance(tokens[1], pf.Space)
        assert isinstance(tokens[2], pf.Str) and tokens[2].text == "world"

    def test_multiple_consecutive_spaces_collapse(self):
        tokens = tokenize_text("Hello    world")
        assert len(tokens) == 3
        assert isinstance(tokens[0], pf.Str)
        assert isinstance(tokens[1], pf.Space)
        assert isinstance(tokens[2], pf.Str)

    def test_hard_linebreaks(self):
        tokens = tokenize_text("Line 1\nLine 2")
        assert len(tokens) == 7
        assert isinstance(tokens[0], pf.Str) and tokens[0].text == "Line"
        assert isinstance(tokens[1], pf.Space)
        assert isinstance(tokens[2], pf.Str) and tokens[2].text == "1"
        assert isinstance(tokens[3], pf.LineBreak)
        assert isinstance(tokens[4], pf.Str) and tokens[4].text == "Line"
        assert isinstance(tokens[5], pf.Space)
        assert isinstance(tokens[6], pf.Str) and tokens[6].text == "2"

    def test_soft_breaks(self):
        tokens = tokenize_text("Line 1\nLine 2", soft_breaks=True)
        assert any(isinstance(t, pf.SoftBreak) for t in tokens)
        assert not any(isinstance(t, pf.LineBreak) for t in tokens)

    def test_empty_lines_in_tokenize_text(self):
        tokens = tokenize_text("Line 1\n\nLine 2")
        # Line 1, Space, 1, LineBreak, LineBreak, Line, Space, 2
        linebreaks = [t for t in tokens if isinstance(t, pf.LineBreak)]
        assert len(linebreaks) == 2

    def test_string_alias(self):
        assert string("test string") == tokenize_text("test string")


class TestAttributeSanitizers:
    """Verify class, attribute, and ID normalization."""

    def test_clean_classes_none_and_str(self):
        assert clean_classes(None) == []
        assert clean_classes("") == []
        assert clean_classes(".btn .btn-primary") == ["btn", "btn-primary"]

    def test_clean_classes_iterable(self):
        assert clean_classes([".highlight", "important", ""]) == ["highlight", "important"]
        assert clean_classes([123, ".badge"]) == ["123", "badge"]
        assert clean_classes(123) == ["123"]

    def test_clean_attributes(self):
        assert clean_attributes(None) == {}
        assert clean_attributes({"width": 100, "data-test": "val"}) == {
            "width": "100",
            "data-test": "val",
        }

    def test_clean_identifier(self):
        assert clean_identifier(None) == ""
        assert clean_identifier("") == ""
        assert clean_identifier("#section-title") == "section-title"
        assert clean_identifier("already-clean") == "already-clean"


class TestCoreWrappers:
    """Verify basic AST constructor helpers."""

    def test_space_and_breaks(self):
        assert isinstance(space(), pf.Space)
        assert isinstance(line_break(), pf.LineBreak)
        assert isinstance(soft_break(), pf.SoftBreak)

    def test_math_wrappers(self):
        m_in = math_inline("x + y")
        assert isinstance(m_in, pf.Math)
        assert m_in.format == "InlineMath"
        assert m_in.text == "x + y"

        m_disp = math_display("E = mc^2")
        assert isinstance(m_disp, pf.Math)
        assert m_disp.format == "DisplayMath"
        assert m_disp.text == "E = mc^2"

    def test_plain_and_para(self):
        pl = plain("Hello world")
        assert isinstance(pl, pf.Plain)
        assert len(pl.content) == 3

        pr = para("Paragraph text")
        assert isinstance(pr, pf.Para)
        assert len(pr.content) == 3

    def test_raw_inline_and_block_format_resolution(self):
        raw_inl = raw_inline("<span>test</span>", format="html")
        assert isinstance(raw_inl, pf.RawInline)
        assert raw_inl.format == "html"

        # Check global TARGET_FORMAT resolution with Format enum
        md.TARGET_FORMAT = Format.LATEX
        raw_blk = raw_block("\\textbf{test}")
        assert isinstance(raw_blk, pf.RawBlock)
        assert raw_blk.format == "latex"

        # Check string TARGET_FORMAT
        md.TARGET_FORMAT = "revealjs"
        raw_rvl = raw_block("<section>test</section>")
        assert raw_rvl.format == "html"

        md.TARGET_FORMAT = "docx"
        raw_docx = raw_block("test")
        assert raw_docx.format == "docx"

        md.TARGET_FORMAT = None


class TestAsInlinesCoercion:
    """Verify coercion into flat lists of Panflute Inline elements."""

    def test_primitives(self):
        inlines = as_inlines("hello", 42, 3.14)
        assert all(isinstance(i, pf.Inline) for i in inlines)
        assert any(isinstance(i, pf.Str) and i.text == "42" for i in inlines)

    def test_none_skipped(self):
        inlines = as_inlines(None, "word", None)
        assert len(inlines) == 1
        assert inlines[0].text == "word"

    def test_nested_iterables_flattened(self):
        inlines = as_inlines(["one", ["two", ("three", 4)]])
        texts = [i.text for i in inlines if isinstance(i, pf.Str)]
        assert texts == ["one", "two", "three", "4"]

    def test_latex_token_coercion(self):
        v = tex.var("theta", 45)
        inlines = as_inlines("Angle: ", v)
        math_nodes = [i for i in inlines if isinstance(i, pf.Math)]
        assert len(math_nodes) == 1
        assert math_nodes[0].format == "InlineMath"
        assert "theta" in math_nodes[0].text

    def test_block_raises_panflute_type_error(self):
        with pytest.raises(PanfluteTypeError) as exc_info:
            as_inlines(pf.Para(pf.Str("illegal")))
        assert "Invalid element type: expected Inline element" in str(exc_info.value)

    def test_unsupported_object_raises_type_error(self):
        with pytest.raises(PanfluteTypeError):
            as_inlines(object())


class TestAsBlocksCoercion:
    """Verify coercion into flat lists of Panflute Block elements."""

    def test_existing_block_preserved(self):
        b1 = pf.HorizontalRule()
        b2 = pf.Header(pf.Str("Title"), level=1)
        res = as_blocks(b1, b2)
        assert res == [b1, b2]

    def test_consecutive_inlines_grouped_into_para(self):
        res = as_blocks("Hello", pf.Space(), "world")
        assert len(res) == 1
        assert isinstance(res[0], pf.Para)
        assert len(res[0].content) == 3

    def test_interleaved_inlines_and_blocks(self):
        res = as_blocks(
            "First para",
            pf.HorizontalRule(),
            "Second para",
        )
        assert len(res) == 3
        assert isinstance(res[0], pf.Para)
        assert isinstance(res[1], pf.HorizontalRule)
        assert isinstance(res[2], pf.Para)

    def test_as_blocks_with_latex_tokens_and_numbers(self):
        v = tex.var("y", 10)
        res = as_blocks("Equation:", v, 99)
        assert len(res) == 1
        assert isinstance(res[0], pf.Para)
        math_nodes = [i for i in res[0].content if isinstance(i, pf.Math)]
        assert len(math_nodes) == 1

    def test_as_blocks_invalid_type_raises(self):
        with pytest.raises(PanfluteTypeError):
            as_blocks(object())


class TestCellAndContainerCoercion:
    """Verify as_cells, as_plain_or_para, ensure_inline, and ensure_block."""

    def test_as_cells(self):
        cells = as_cells("A", 42, pf.TableCell(pf.Plain(pf.Str("Custom"))))
        assert len(cells) == 3
        assert all(isinstance(c, pf.TableCell) for c in cells)

    def test_as_plain_or_para(self):
        pl = as_plain_or_para("Text", plain=True)
        assert isinstance(pl, pf.Plain)

        pr = as_plain_or_para("Text", plain=False)
        assert isinstance(pr, pf.Para)

        # Existing block passed through unchanged
        hr = pf.HorizontalRule()
        assert as_plain_or_para(hr) is hr

    def test_ensure_inline(self):
        single = pf.Str("word")
        assert ensure_inline(single) is single

        multi = ensure_inline("two words")
        assert isinstance(multi, pf.Span)

        with pytest.raises(PanfluteTypeError):
            ensure_inline(pf.BlockQuote())

    def test_ensure_block(self):
        b = pf.HorizontalRule()
        assert ensure_block(b) is b

        wrapped = ensure_block("text")
        assert isinstance(wrapped, pf.Para)

        multi = ensure_block([pf.Para(pf.Str("P1")), pf.Para(pf.Str("P2"))])
        assert isinstance(multi, pf.Div)
