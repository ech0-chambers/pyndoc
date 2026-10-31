"""Typographical accents, diacritics, font styling, and multi-line layout formatting."""

import re

from .core import Macro, Token, as_token


def sanitise_latex_text(text_val: str) -> str:
    """Escape special LaTeX characters in text."""
    replacements = [
        ("\\", "\\textbackslash "),
        ("{", "\\{"),
        ("}", "\\}"),
        ("$", "\\$"),
        ("&", "\\&"),
        ("#", "\\#"),
        ("_", "\\_"),
        ("%", "\\%"),
        ("~", "\\textasciitilde "),
        ("|", "\\textbar "),
        ("<", "\\textless "),
        (">", "\\textgreater "),
    ]
    for old, new in replacements:
        text_val = re.sub(rf"(?<!\\){re.escape(old)}", new, text_val)
    return text_val


def text(content: str) -> Macro:
    """Encapsulate text in LaTeX `\\text` macro with escaping."""
    return Macro("text", sanitise_latex_text(content))


def texttt(content: str) -> Macro:
    """Encapsulate text in LaTeX `\\texttt` (typewriter font) macro with escaping."""
    return Macro("texttt", sanitise_latex_text(content))


def textbf(content: str) -> Macro:
    """Encapsulate text in LaTeX `\\textbf` (bold font) macro with escaping."""
    return Macro("textbf", sanitise_latex_text(content))


def textit(content: str) -> Macro:
    """Encapsulate text in LaTeX `\\textit` (italic font) macro with escaping."""
    return Macro("textit", sanitise_latex_text(content))


def textsc(content: str) -> Macro:
    """Encapsulate text in LaTeX `\\textsc` (small caps font) macro with escaping."""
    return Macro("textsc", sanitise_latex_text(content))


def mathbf(content: Token | str | float) -> Macro:
    """Encapsulate math expression in LaTeX `\\mathbf` (bold math font)."""
    return Macro("mathbf", as_token(content))


def mathrm(content: Token | str | float) -> Macro:
    """Encapsulate math expression in LaTeX `\\mathrm` (roman upright math font)."""
    return Macro("mathrm", as_token(content))


def mathbb(content: Token | str | float) -> Macro:
    """Encapsulate math expression in LaTeX `\\mathbb` (blackboard bold math font)."""
    return Macro("mathbb", as_token(content))


def mathcal(content: Token | str | float) -> Macro:
    """Encapsulate math expression in LaTeX `\\mathcal` (calligraphic math font)."""
    return Macro("mathcal", as_token(content))


def boldsymbol(content: Token | str | float) -> Macro:
    """Encapsulate math expression in LaTeX `\\boldsymbol` (bold symbol font)."""
    return Macro("boldsymbol", as_token(content))


bm = boldsymbol


def dot(expr: Token | str | float) -> Macro:
    """Add a dot above the following expression, such as `\\dot{a}`."""
    return Macro("dot", expr)


def ddot(expr: Token | str | float) -> Macro:
    """Add a double dot above the following expression, such as `\\ddot{a}`."""
    return Macro("ddot", expr)


def hat(expr: Token | str | float) -> Macro:
    """Add a hat above the following expression, such as `\\hat{a}`."""
    return Macro("hat", expr)


def bar(expr: Token | str | float) -> Macro:
    """Add a bar above the following expression, such as `\\bar{a}`."""
    return Macro("bar", expr)


def vec(expr: Token | str | float) -> Macro:
    """Add a vector arrow above the following expression, such as `\\vec{a}`."""
    return Macro("vec", expr)


def underline(expr: Token | str | float) -> Macro:
    """Add an underline below the following expression, such as `\\underline{a}`."""
    return Macro("underline", expr)


def tilde(expr: Token | str | float) -> Macro:
    """Add a tilde above the following expression, such as `\\tilde{a}`."""
    return Macro("tilde", expr)


def widehat(expr: Token | str | float) -> Macro:
    """Add a wide hat above the following expression, such as `\\widehat{a}`."""
    return Macro("widehat", expr)


def widebar(expr: Token | str | float) -> Macro:
    """Add a wide bar above the following expression, such as `\\widebar{a}`."""
    return Macro("widebar", expr)


overline = widebar


def widetilde(expr: Token | str | float) -> Macro:
    """Add a wide tilde above the following expression, such as `\\widetilde{a}`."""
    return Macro("widetilde", expr)


def split(
    lines: list[str | Token | tuple[str | Token, ...]],
    environment: str = "split",
    separator: str | None = "=",
) -> str:
    """Format multiple lines inside a LaTeX split-like environment."""
    if not isinstance(lines, (list, tuple)):
        lines = [lines]
    formatted_lines: list[str] = []
    for line in lines:
        if isinstance(line, (list, tuple)):
            if len(line) == 1:
                formatted_lines.append(f"& {separator if separator is not None else '='} {line[0]}")
            else:
                if separator is None:
                    formatted_lines.append(" & ".join(str(expr) for expr in line))
                elif len(line) == 2:
                    formatted_lines.append(f"{line[0]} & {separator} {line[1]}")
                else:
                    formatted_lines.append(
                        f"{line[0]} & {separator} {line[1]} & "
                        + " & ".join(str(expr) for expr in line[2:])
                    )
        else:
            formatted_lines.append(str(line))
    return (
        f"\\begin{{{environment}}}\n\t"
        + "\\\\\n\t".join(formatted_lines)
        + f"\n\\end{{{environment}}}"
    )


__all__ = [
    "sanitise_latex_text",
    "text",
    "texttt",
    "textbf",
    "textit",
    "textsc",
    "mathbf",
    "mathrm",
    "mathbb",
    "mathcal",
    "boldsymbol",
    "bm",
    "dot",
    "ddot",
    "hat",
    "bar",
    "vec",
    "underline",
    "tilde",
    "widehat",
    "widebar",
    "overline",
    "widetilde",
    "split",
]
