"""Unit tests for pyndoc.markdown element constructors (inlines, blocks, lists, tables)."""

import panflute as pf
import pytest

import pyndoc.latex as tex
import pyndoc.markdown as md
from pyndoc.markdown.coercion import PanfluteTypeError, PanfluteValueError


class TestInlines:
    """Verify inline styling, code, math, links, and nested formatting."""

    def test_bold_and_nested_italic(self):
        # Crucial test: md.bold(md.italic("hello")) used to crash with:
        # TypeError: panflute.elements.Strong() argument after * must be an iterable, not Emph
        b = md.bold(md.italic("nested"))
        assert isinstance(b, pf.Strong)
        assert len(b.content) == 1
        assert isinstance(b.content[0], pf.Emph)

        # Bold containing a LaTeX Token
        v = tex.var("z", 100)
        b_tok = md.bold("Value of z: ", v)
        assert isinstance(b_tok, pf.Strong)
        assert any(isinstance(node, pf.Math) for node in b_tok.content)

    def test_inline_styles(self):
        assert isinstance(md.italic("it"), pf.Emph)
        assert isinstance(md.strikethrough("strike"), pf.Strikeout)
        assert isinstance(md.underline("under"), pf.Underline)
        assert isinstance(md.superscript("super"), pf.Superscript)
        assert isinstance(md.subscript("sub"), pf.Subscript)
        assert isinstance(md.small_caps("caps"), pf.SmallCaps)

    def test_code_with_language(self):
        c = md.code("print(1)", language="python")
        assert isinstance(c, pf.Code)
        assert c.text == "print(1)"
        assert "python" in c.classes

    def test_math_inline_and_display(self):
        m_in = md.inline_math("a^2 + b^2 = c^2")
        assert isinstance(m_in, pf.Math)
        assert m_in.format == "InlineMath"

        eq = md.equation("e^{i\\pi} + 1 = 0", label="euler")
        assert isinstance(eq, pf.Para)
        assert any(isinstance(node, pf.Math) and node.format == "DisplayMath" for node in eq.content)
        assert any(isinstance(node, pf.Str) and "#eq:euler" in node.text for node in eq.content)

    def test_link_url_inference(self):
        # Anchor links must NOT have https:// prepended
        anchor_link = md.link("Go to Section", url="#sec-1")
        assert anchor_link.url == "#sec-1"

        # Text with spaces must NOT have https:// prepended (no false positive)
        text_link = md.link("Click here to download")
        assert text_link.url == ""

        # Web URL starting with www. gets https:// prepended
        web_link = md.link("www.example.com")
        assert web_link.url == "https://www.example.com"

        # Relative file links stay relative
        file_link = md.link("data.csv")
        assert file_link.url == "data.csv"

        # Email address gets mailto: prepended
        email_link = md.link("user@example.com")
        assert email_link.url == "mailto:user@example.com"

        # Explicit URL preserved
        expl_link = md.link("Pyndoc", url="https://github.com/example/pyndoc")
        assert expl_link.url == "https://github.com/example/pyndoc"

    def test_image(self):
        img = md.image("fig.png", "A nice figure", title="Figure 1")
        assert isinstance(img, pf.Image)
        assert img.url == "fig.png"
        assert img.title == "Figure 1"

    def test_footnote(self):
        fn = md.footnote("See appendix A")
        assert isinstance(fn, pf.Note)
        assert isinstance(fn.content[0], pf.Plain)

    def test_citation_and_cite(self):
        c = md.citation("smith2020", prefix="see", suffix="p. 42")
        assert isinstance(c, pf.Citation)
        assert c.id == "smith2020"

        # Call cite with Citation object
        cite_node = md.cite(c)
        assert isinstance(cite_node, pf.Cite)
        assert len(cite_node.citations) == 1
        assert cite_node.citations[0].id == "smith2020"

        # Call cite with text and key
        cite_text = md.cite("Smith demonstrated that", "smith2020")
        assert isinstance(cite_text, pf.Cite)
        assert cite_text.citations[0].id == "smith2020"

    def test_span(self):
        sp = md.span("styled text", classes=[".warning"], identifier="warning-msg")
        assert isinstance(sp, pf.Span)
        assert sp.identifier == "warning-msg"
        assert sp.classes == ["warning"]


class TestBlocks:
    """Verify block constructors: paragraph, header, block_quote, code_block, rule, figure, div."""

    def test_paragraph_and_plain(self):
        p = md.paragraph("Hello", "world")
        assert isinstance(p, pf.Para)
        assert len(p.content) == 2

    def test_header_valid_levels(self):
        h1 = md.header("Title", level=1, identifier="main-title")
        assert isinstance(h1, pf.Header)
        assert h1.level == 1
        assert h1.identifier == "main-title"

        h6 = md.header("Sub-sub-sub", level=6)
        assert h6.level == 6

    def test_header_invalid_level_raises(self):
        with pytest.raises(PanfluteValueError) as exc_info:
            md.header("Bad", level=7)
        assert "Heading level must be between 1 and 6" in str(exc_info.value)

    def test_block_quote(self):
        bq = md.block_quote("Quote line 1", md.paragraph("Quote line 2"))
        assert isinstance(bq, pf.BlockQuote)
        assert all(isinstance(child, pf.Block) for child in bq.content)

    def test_code_block(self):
        cb = md.code_block("def foo():\n    return 42", language="python")
        assert isinstance(cb, pf.CodeBlock)
        assert "python" in cb.classes

    def test_horizontal_rule(self):
        assert isinstance(md.horizontal_rule(), pf.HorizontalRule)
        assert isinstance(md.rule(), pf.HorizontalRule)

    def test_div(self):
        d = md.div(md.paragraph("Inside div"), classes=[".notes"])
        assert isinstance(d, pf.Div)
        assert d.classes == ["notes"]

    def test_figure_and_caption(self):
        fig = md.figure("plot.svg", "Chart caption", short_caption="Chart")
        assert isinstance(fig, pf.Figure)
        assert fig.caption is not None
        assert isinstance(fig.caption, pf.Caption)

    def test_figure_with_existing_caption_object(self):
        raw_cap = pf.Caption(pf.Plain(pf.Str("Pre-made caption")))
        fig = md.figure("img.png", raw_cap)
        assert fig.caption is raw_cap

        cap2 = md.figure_caption(raw_cap)
        assert cap2 is raw_cap

    def test_as_blocks_token_between_blocks_rendered_as_display_math(self):
        v = tex.var("alpha", 1.5)
        b1 = pf.Header(pf.Str("Intro"), level=1)
        b2 = pf.HorizontalRule()

        # Standalone token -> DisplayMath
        standalone_res = md.as_blocks(v)
        assert len(standalone_res) == 1
        assert isinstance(standalone_res[0], pf.Para)
        assert isinstance(standalone_res[0].content[0], pf.Math)
        assert standalone_res[0].content[0].format == "DisplayMath"

        # Token between two blocks -> DisplayMath
        between_res = md.as_blocks(b1, v, b2)
        assert len(between_res) == 3
        assert between_res[0] is b1
        assert isinstance(between_res[1], pf.Para)
        assert between_res[1].content[0].format == "DisplayMath"
        assert between_res[2] is b2

        # Token mixed with inlines -> InlineMath
        mixed_res = md.as_blocks("The parameter is ", v, ".")
        assert len(mixed_res) == 1
        assert isinstance(mixed_res[0], pf.Para)
        math_nodes = [n for n in mixed_res[0].content if isinstance(n, pf.Math)]
        assert len(math_nodes) == 1
        assert math_nodes[0].format == "InlineMath"


class TestLists:
    """Verify bullet list, ordered list, list item, and definition list."""

    def test_bullet_list_flat(self):
        bl = md.bullet_list(["Item 1", "Item 2", "Item 3"])
        assert isinstance(bl, pf.BulletList)
        assert len(bl.content) == 3
        assert all(isinstance(item, pf.ListItem) for item in bl.content)

    def test_bullet_list_nested_tuple_tree(self):
        bl = md.bullet_list([
            ("Parent", ["Child 1", "Child 2"]),
            "Sibling",
        ])
        assert isinstance(bl, pf.BulletList)
        assert len(bl.content) == 2
        parent_item = bl.content[0]
        # Content has main block and sub-bullet list
        assert any(isinstance(sub, pf.BulletList) for sub in parent_item.content)

    def test_ordered_list_with_enums(self):
        ol = md.ordered_list(
            ["Step 1", "Step 2"],
            enumeration=md.Enumeration.ROMAN_LOWER,
            delimiter=md.ListDelimiter.TWO_PAREN,
        )
        assert isinstance(ol, pf.OrderedList)
        assert ol.style == "LowerRoman"
        assert ol.delimiter == "TwoParens"

    def test_ordered_list_invalid_enum_raises(self):
        with pytest.raises(PanfluteValueError):
            md.ordered_list(["1"], enumeration="invalid_style")

    def test_strenum_properties(self):
        assert md.Enumeration.DECIMAL == "Decimal"
        assert md.Enumeration.ROMAN_LOWER == "LowerRoman"
        assert md.ListDelimiter.PERIOD == "Period"
        assert md.ListDelimiter.TWO_PAREN == "TwoParens"

    def test_definition_list(self):
        dl = md.definition_list({
            "Term 1": "Definition 1",
            "Term 2": ["Def 2a", "Def 2b"],
        })
        assert isinstance(dl, pf.DefinitionList)
        assert len(dl.content) == 2


class TestTables:
    """Verify table construction from 2D sequences, dictionaries, and custom configurations."""

    def test_table_from_2d_sequence(self):
        tbl = md.table(
            data=[["Alice", 95], ["Bob", 88]],
            headers=["Name", "Score"],
        )
        assert isinstance(tbl, pf.Table)
        assert tbl.head is not None
        assert len(tbl.head.content[0].content) == 2
        # Body has 2 rows
        assert len(tbl.content[0].content) == 2

    def test_table_from_dict(self):
        tbl = md.table(
            data={"Product": ["Widget", "Gadget"], "Price": [19.99, 29.99]},
        )
        assert isinstance(tbl, pf.Table)
        assert tbl.head is not None
        # Headers extracted from dict keys
        headers = [pf.stringify(cell) for cell in tbl.head.content[0].content]
        assert "Product" in headers
        assert "Price" in headers

    def test_table_numeric_alignment_inference(self):
        # 1st col text -> AlignDefault, 2nd col numbers -> AlignRight
        tbl = md.table(
            data=[["A", 10], ["B", 20], ["C", 30]],
            headers=["Letter", "Value"],
        )
        colspec = tbl.colspec
        assert colspec[0][0] == "AlignDefault"
        assert colspec[1][0] == "AlignRight"

    def test_table_custom_alignments_and_widths(self):
        tbl = md.table(
            data=[["A", "B"]],
            alignments=["center", "right"],
            widths=[0.4, 0.6],
            caption="Comparison Table",
        )
        colspec = tbl.colspec
        assert colspec[0] == ("AlignCenter", 0.4)
        assert colspec[1] == ("AlignRight", 0.6)
        assert tbl.caption is not None

    def test_table_alignment_strenum(self):
        assert md.Alignment.LEFT == "AlignLeft"
        assert md.Alignment.CENTER == "AlignCenter"
        assert md.Alignment.RIGHT == "AlignRight"
        assert md.Alignment.DEFAULT == "AlignDefault"

        tbl = md.table(
            data=[["A", "B"]],
            alignments=[md.Alignment.LEFT, md.Alignment.RIGHT],
        )
        assert tbl.colspec[0][0] == "AlignLeft"
        assert tbl.colspec[1][0] == "AlignRight"

    def test_table_with_existing_caption_object(self):
        raw_cap = pf.Caption(pf.Plain(pf.Str("My table caption")))
        tbl = md.table([[1]], caption=raw_cap)
        assert tbl.caption is raw_cap

    def test_table_empty_data_raises(self):
        with pytest.raises(PanfluteValueError):
            md.table(data=[])

    def test_table_unsupported_data_type_raises(self):
        with pytest.raises(PanfluteTypeError):
            md.table(data=12345)

    def test_table_from_numpy_array(self):
        import numpy as np

        arr = np.array([[1.5, 2.5], [3.5, 4.5]])
        tbl = md.table(arr, headers=["X", "Y"])
        assert isinstance(tbl, pf.Table)
        assert len(tbl.content[0].content) == 2

    def test_table_head_body_foot_helpers(self):
        r1 = md.table_row("A", "B")
        r2 = md.table_row("C", "D")
        head = md.table_head(r1)
        body = md.table_body(r2)
        foot = md.table_foot(r1)
        assert isinstance(head, pf.TableHead)
        assert isinstance(body, pf.TableBody)
        assert isinstance(foot, pf.TableFoot)

    def test_raw_blocks_and_inlines(self):
        r_blk = md.raw("<div>block</div>", format="html")
        assert isinstance(r_blk, pf.RawBlock)
        r_inl = md.raw("<span>inline</span>", format="html", inline=True)
        assert isinstance(r_inl, pf.RawInline)

    def test_convert_from_string_simple(self):
        elems = md.convert_from_string("# Header\n\nSome text")
        assert isinstance(elems, list)
        assert any(isinstance(e, pf.Header) for e in elems)
        assert any(isinstance(e, pf.Para) for e in elems)
