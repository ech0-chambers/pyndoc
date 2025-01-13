from enum import Enum, auto
from pathlib import Path
import subprocess
from typing import Any, List, Optional
import panflute as pf
import logging

TARGET_FORMAT = None


"""
This module contains functions to act as a wrapper around panflute classes to make them more convenient to create from scratch.
"""


def snake_to_camel(s: str) -> str:
    return "".join(word.capitalize() for word in s.split("_"))


def join_list(items: list[Any], sep: Any, flatten: bool = False) -> list[Any]:
    # join_list([1, 2, 3], 0) -> [1, 0, 2, 0, 3]
    out = []
    if len(items) == 0:
        return out
    if len(items) == 1:
        return items
    for i, item in enumerate(items[:-1]):
        if flatten and isinstance(item, (tuple, list)):
            out.extend(item)
        else:
            out.append(item)
        if flatten and isinstance(sep, (tuple, list)):
            out.extend(sep)
        else:
            out.append(sep)
    out.append(items[-1])
    return out


def string(s: str) -> List[pf.Inline]:
    """Convert a string to a panflute Element, without any parsing.

    Parameters
    ----------
    s : str
        _description_

    Returns
    -------
    List[pf.Inline]
        The panflute element.
    """    
    lines = s.split("\n")
    for i, line in enumerate(lines):
        words = line.split(" ")
        for j, word in enumerate(words):
            words[j] = pf.Str(word)
        lines[i] = join_list(words, pf.Space)
    out = join_list(lines, pf.LineBreak, flatten=True)
    if len(out) == 1:
        if isinstance(out[0], (tuple, list)):
            return out[0]
    return out


def block_quote(*args) -> pf.BlockQuote:
    """Create a block quote element.

    Returns
    -------
    pf.BlockQuote
        The block quote element.
    """    
    return pf.BlockQuote(*args)


def list_item(item):
    if isinstance(item, str):
        return pf.ListItem(pf.Plain(*string(item)))
    #
    elif isinstance(item, (float, int)):
        return pf.ListItem(pf.Plain(*string(str(item))))
    #
    elif isinstance(item, (tuple, list)):
        out_item = pf.ListItem(pf.Plain())
        out_item.content.append(bullet_list(item))
        return out_item
    #
    elif isinstance(item, pf.Block):
        return pf.ListItem(item)
    #
    elif isinstance(item, pf.ListItem):
        return item
    #
    elif isinstance(item, pf.Inline):
        return pf.ListItem(pf.Plain(item))
    #
    else:
        raise ValueError(f"Unknown item type: {type(item)}")


def bullet_list(items):
    list_items = []
    skip = False
    for i, item in enumerate(items):
        if skip:
            skip = False
            continue
        new_item = list_item(item)
        if i + 1 < len(items):
            if isinstance(items[i + 1], (tuple, list)):
                skip = True
                new_item.content.append(bullet_list(items[i + 1]))
            elif isinstance(items[i + 1], (pf.BulletList, pf.OrderedList)):
                skip = True
                new_item.content.append(items[i + 1])

        list_items.append(new_item)
    return pf.BulletList(*list_items)


class Enumeration(Enum):
    ARABIC = 0
    ALPH_LOWER = auto()
    ALPH_UPPER = auto()
    ROMAN_LOWER = auto()
    ROMAN_UPPER = auto()
    EXAMPLE = auto()
    DEFAULT = auto()


class ListDelimiter(Enum):
    PERIOD = 0
    ONE_PAREN = auto()
    TWO_PAREN = auto()
    DEFAULT = auto()


def ordered_list(
    items,
    enumeration: Optional[Enumeration] = None,
    start: int = 1,
    delimiter: Optional[ListDelimiter] = None,
):
    list_items = []
    skip = False
    for i, item in enumerate(items):
        if skip:
            skip = False
            continue
        new_item = list_item(item)
        if i + 1 < len(items):
            if isinstance(items[i + 1], (tuple, list)):
                skip = True
                new_item.content.append(ordered_list(items[i + 1]))
            elif isinstance(items[i + 1], (pf.BulletList, pf.OrderedList)):
                skip = True
                new_item.content.append(items[i + 1])
        list_items.append(new_item)

    if enumeration is None:
        enumeration = Enumeration.DEFAULT
    if delimiter is None:
        delimiter = ListDelimiter.DEFAULT

    match enumeration:
        case Enumeration.ARABIC:
            style = "Decimal"
        case Enumeration.ALPH_LOWER:
            style = "LowerAlpha"
        case Enumeration.ALPH_UPPER:
            style = "UpperAlpha"
        case Enumeration.ROMAN_LOWER:
            style = "LowerRoman"
        case Enumeration.ROMAN_UPPER:
            style = "UpperRoman"
        case Enumeration.EXAMPLE:
            style = "Example"
        case Enumeration.DEFAULT:
            style = "DefaultStyle"

    match delimiter:
        case ListDelimiter.PERIOD:
            delim = "Period"
        case ListDelimiter.ONE_PAREN:
            delim = "OneParen"
        case ListDelimiter.TWO_PAREN:
            delim = "TwoParens"
        case ListDelimiter.DEFAULT:
            delim = "DefaultDelim"

    return pf.OrderedList(
        *list_items,
        style=style,
        start=start,
        delimiter=delim,
    )


def citation(
    id: str,
    mode: str = "NormalCitation",
    prefix: Optional[str | pf.Inline] = None,
    suffix: Optional[str | pf.Inline] = None,
    note_num: int = 0,
    hash: int = 0,
):
    if prefix is not None:
        if isinstance(prefix, str):
            prefix = pf.Str(prefix)
    else:
        prefix = ""
    if suffix is not None:
        if isinstance(suffix, str):
            suffix = pf.Str(suffix)
    else:
        suffix = ""
    return pf.Citation(
        id=id,
        mode=mode,
        prefix=prefix,
        suffix=suffix,
        note_num=note_num,
        hash=hash,
    )


def cite(
    contents: list[pf.Inline | str] | pf.Inline | str,
    citations: list[pf.Citation | str] | pf.Citation | str,
):
    if isinstance(contents, str | pf.Inline):
        contents = [contents]
    if isinstance(citations, str | pf.Citation):
        citations = [citations]
    for i, content in enumerate(contents):
        if isinstance(content, str):
            contents[i] = pf.Str(content)
    for i, c in enumerate(citations):
        if isinstance(c, str):
            citations[i] = citation(c)
    return pf.Cite(
        pf.Plain(*contents),
        citations,
    )


def code(
    text: str,
    identifier: Optional[str] = None,
    classes: Optional[list[str] | str] = None,
    attributes: Optional[dict[str, str]] = None,
    inline: bool = True,
):
    if classes is not None:
        if isinstance(classes, str):
            classes = classes.split()
    else:
        classes = []
    classes = [c.lstrip(".") for c in classes]
    if len(classes) == 0 and not inline:
        classes = [
            ""
        ]  # empty pf.Str is a valid class. Otherwise, panflute does something strange with a html comment (?)
    if identifier is None:
        identifier = ""
    if attributes is None:
        attributes = {}
    constructor = pf.Code if inline else pf.CodeBlock
    return constructor(
        text=text,
        identifier=identifier,
        classes=classes,
        attributes=attributes,
    )


def code_block(
    text: str,
    identifier: Optional[str] = None,
    classes: Optional[list[str] | str] = None,
    attributes: Optional[dict[str, str]] = None,
):
    return code(text, identifier, classes, attributes, inline=False)


def paragraph(
    contents: list[pf.Inline | str] | pf.Inline | str,
):
    if isinstance(contents, str | pf.Inline):
        contents = [contents]
    for i, content in enumerate(contents):
        if isinstance(content, str):
            contents[i] = pf.Str(content)
    return pf.Para(*contents)


def header(
    text: str | pf.Inline,
    level: int = 1,
    identifier: Optional[str] = None,
    classes: Optional[list[str] | str] = None,
):
    logging.debug(f"Text: {text}\n\tType: {type(text)}")
    if isinstance(text, str):
        text = string(text)
    logging.debug(f"Text: {text}\n\tType: {type(text)}")
    if not isinstance(text, (tuple, list)):
        text = [text]
    logging.debug(f"Text: {text}\n\tType: {type(text)}")
    if classes is not None:
        if isinstance(classes, str):
            classes = classes.split()
    else:
        classes = []
    classes = [c.lstrip(".") for c in classes]
    if identifier is None:
        identifier = ""
    return pf.Header(
        *text,
        level=level,
        identifier=identifier,
        classes=classes,
        attributes={},
    )


def link(
    text: str | pf.Inline,
    url: Optional[str] = None,
    title: Optional[str] = None,
    identifier: Optional[str] = None,
    classes: Optional[list[str] | str] = None,
    attributes: Optional[dict[str, str]] = None,
):
    if url is None:
        if isinstance(text, str):
            url = text
            if "://" not in url:
                url = f"https://{url}"
        else:
            url = ""
    if isinstance(text, str):
        text = string(text)
    if title is None:
        title = ""
    if classes is not None:
        if isinstance(classes, str):
            classes = classes.split()
    else:
        classes = []
    classes = [c.lstrip(".") for c in classes]
    if identifier is None:
        identifier = ""
    if attributes is None:
        attributes = {}
    return pf.Link(
        *text,
        url=url,
        title=title,
        identifier=identifier,
        classes=classes,
        attributes=attributes,
    )


def rule():
    return pf.HorizontalRule()


def italic(
    text: str | pf.Inline,
):
    if isinstance(text, str):
        text = string(text)
    return pf.Emph(*text)


def bold(
    text: str | pf.Inline,
):
    if isinstance(text, str):
        text = string(text)
    return pf.Strong(*text)


def strikethrough(
    text: str | pf.Inline,
):
    if isinstance(text, str):
        text = string(text)
    return pf.Strikeout(*text)


def underline(
    text: str | pf.Inline,
):
    if isinstance(text, str):
        text = string(text)
    return pf.Underline(*text)


def superscript(
    text: str | pf.Inline,
):
    if isinstance(text, str):
        text = string(text)
    return pf.Superscript(*text)


def subscript(
    text: str | pf.Inline,
):
    if isinstance(text, str):
        text = string(text)
    return pf.Subscript(*text)


def small_caps(
    text: str | pf.Inline,
):
    if isinstance(text, str):
        text = string(text)
    return pf.SmallCaps(*text)


def footnote(
    text: str | pf.Inline,
):
    if isinstance(text, str):
        text = string(text)
    return pf.Note(pf.Plain(*text))


def math(text: str, display: bool = False, label: Optional[str] = None):
    if isinstance(display, str):
        display = display.lower() == "true"
    if not isinstance(text, str):
        text = str(text)
    el = pf.Math(
        text=text,
        format="DisplayMath" if display else "InlineMath",
    )
    if display:
        if label is not None:
            if not label.startswith("#eq:"):
                label = f"#eq:{label}"
            return pf.Para(el, pf.Str("{" + label + "}"))
        return pf.Para(el)
    return el


def equation(text: str, label: Optional[str] = None):
    return math(text, display=True, label=label)

# TODO: Add label support for equations. See how pandoc-crossref does it?
# Done (?)
# Add to figures too? May or may not be necessary


def inline_math(text: str):
    return math(text, display=False)


def image(
    url: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    identifier: Optional[str] = None,
    classes: Optional[list[str] | str] = None,
    attributes: Optional[dict[str, str]] = None,
):
    if title is None:
        title = ""

    if description is None:
        description = ""
    if isinstance(description, str):
        description = string(description)

    if classes is not None:
        if isinstance(classes, str):
            classes = classes.split()
    else:
        classes = []
    classes = [c.lstrip(".") for c in classes]
    if identifier is None:
        identifier = ""
    if attributes is None:
        attributes = {}
    return pf.Image(
        *description,
        url=url,
        title=title,
        identifier=identifier,
        classes=classes,
        attributes=attributes,
    )


def figure_caption(
    text: str | pf.Inline,
    short_caption: Optional[str | pf.Inline] = None,
    identifier: Optional[str] = None,
):
    if isinstance(text, str):
        text = string(text)
    if short_caption is not None:
        if isinstance(short_caption, str):
            short_caption = string(short_caption)
    else:
        short_caption = string("")
    if identifier is None:
        identifier = ""
    return pf.table_elements.Caption(pf.Plain(*text), short_caption=short_caption)


def figure(
    url: str,
    identifier: Optional[str] = None,
    classes: Optional[list[str] | str] = None,
    attributes: Optional[dict[str, str]] = None,
    caption: Optional[str | pf.Inline] = None,
    image_options: Optional[dict[str, str]] = None,
):
    if caption is not None:
        if isinstance(caption, str):
            caption = string(caption)
    else:
        caption = string("")
    if classes is not None:
        if isinstance(classes, str):
            classes = classes.split()
    else:
        classes = []
    classes = [c.lstrip(".") for c in classes]
    if identifier is None:
        identifier = ""
    if attributes is None:
        attributes = {}
    if image_options is None:
        image_options = {}
    image = pf.Image(
        url=url,
        **image_options,
    )
    return pf.Figure(
        pf.Plain(image),
        caption=figure_caption(caption),
        identifier=identifier,
        classes=classes,
        attributes=attributes,
    )


def raw(
    text: str, format: Optional[str] = None, inline: bool = False
) -> pf.RawBlock | pf.RawInline:
    global TARGET_FORMAT
    if format is None:
        format = TARGET_FORMAT.name.lower()
    if format in ["revealjs", "chunkedhtml"]: #and probably others
        format == "html"
    if inline:
        return pf.RawInline(
            text=text,
            format=format,
        )
    return pf.RawBlock(
        text=text,
        format=format,
    )


def raw_inline(text: str, format: Optional[str] = None):
    return raw(text, format, inline=True)


from pyndoc.preprocess import preprocess as preprocess_text


def convert_from_string(
    text: str, preprocess: bool = False, format: Optional[str] = 'panflute'
) -> str | list[pf.Element]:
    if preprocess:
        if format != "panflute":
            text = preprocess_text(text, target_format = format)
        else:
            text = preprocess_text(text)
    filter_file = Path(__file__).parent / "filter.py"
    if not filter_file.exists():
        raise FileNotFoundError(f"Filter file not found: {filter_file}")
    output = pf.convert_text(
        text,
        input_format="markdown",
        extra_args=[f"--filter={filter_file.resolve().absolute()}"],
        standalone=False,
        output_format = format,
    )
    # output = pf.convert_text(text, input_format="markdown", standalone = False)
    logging.debug(f"Output from markdown conversion: {output}")
    return output


# TODO: Tables
