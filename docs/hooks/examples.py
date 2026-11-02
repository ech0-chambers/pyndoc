from __future__ import annotations

import html as html_lib
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup
from mkdocs.plugins import get_plugin_logger
import panflute

# Ensure local source tree takes precedence
_SRC_DIR = str(Path(__file__).resolve().parent.parent.parent / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from pyndoc.preprocess import no_console, preprocess  # noqa: E402

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page

logger = get_plugin_logger("pyndoc-examples")

# Regex to match code fence openings tagged with .example (optionally with .raises-exception)
EXAMPLE_FENCE_REGEX = re.compile(
    r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})[ \t]*(?:(?:markdown|md)[ \t]+)?(?:"
    r"\{\s*(?P<attrs>[^}]*\.example\b[^}]*)\}"
    r"|\.example\b(?P<attrs2>[^\n]*)"
    r"|example\b(?P<attrs3>[^\n]*)"
    r")[ \t]*$",
    re.MULTILINE,
)


def on_page_markdown(
    markdown: str, page: Page, config: MkDocsConfig, files: Files, **kwargs: Any
) -> str:
    """Normalize example code fences to standard pymdownx superfences format."""

    def _replace_fence(m: re.Match[str]) -> str:
        indent = m.group("indent")
        fence = m.group("fence")
        if m.group("attrs") is not None:
            raw_attrs = m.group("attrs").strip()
            # Clean up and normalize attributes, ensuring .example is first
            cleaned = re.sub(r"\.example\b", "", raw_attrs).strip()
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            attr_str = f" {cleaned}" if cleaned else ""
            return f"{indent}{fence}markdown {{.example{attr_str}}}"
        else:
            attrs = (
                m.group("attrs2") or m.group("attrs3") or ""
            ).strip()
            attr_str = f" {attrs}" if attrs else ""
            return f"{indent}{fence}markdown {{.example{attr_str}}}"

    return EXAMPLE_FENCE_REGEX.sub(_replace_fence, markdown)


def _render_example_to_html(
    raw_markdown: str,
    filter_file: Path,
    raises_exception: bool = False,
    page_path: str = "",
) -> tuple[str, bool]:
    """Execute Pyndoc preprocessing and Pandoc conversion on raw Markdown.

    When `raises_exception` is True, intentional errors are converted as normal
    without logging warnings or triggering error UI blocks.
    """
    if not raw_markdown.strip():
        return ("", False)

    try:
        # Pass a silenced console to prevent rich terminal output during docs builds
        preprocessed = preprocess(
            raw_markdown, target_format="html", console=no_console()
        )
        html_out = panflute.convert_text(
            preprocessed,
            input_format="markdown",
            output_format="html",
            standalone=False,
            extra_args=[f"--filter={filter_file}", "--math-method=mathjax"],
        )

        # In non-exception mode, check if filter caught an in-process error
        if not raises_exception and "Error running code:" in html_out:
            logger.warning(
                "Pyndoc live example on %s produced runtime error: %s",
                page_path or "unknown",
                html_out.strip(),
            )
            err_div = (
                f'<div class="pyndoc-example-error">'
                f'<span class="error-title">Pyndoc Execution Error</span>'
                f"{html_out}"
                f"</div>"
            )
            return (err_div, True)

        return (html_out, False)
    except Exception as exc:
        if raises_exception:
            # Code was expected to raise an error; do not log warning or show special error UI
            err_html = f"<pre><code>{html_lib.escape(str(exc))}</code></pre>"
            return (err_html, False)

        logger.warning(
            "Error rendering Pyndoc live example on %s: %s",
            page_path or "unknown",
            exc,
        )
        err_div = (
            f'<div class="pyndoc-example-error">'
            f'<span class="error-title">Pyndoc Render Error</span>'
            f"<pre><code>{html_lib.escape(str(exc))}</code></pre>"
            f"</div>"
        )
        return (err_div, True)


def on_page_content(
    html: str, page: Page, config: MkDocsConfig, files: Files, **kwargs: Any
) -> str:
    """Transform example code blocks into unified source + live preview boxes."""
    if "example" not in html or "highlight" not in html:
        return html

    soup = BeautifulSoup(html, "html.parser")
    example_divs = soup.select("div.example.highlight")
    if not example_divs:
        return html

    filter_file = (Path(_SRC_DIR) / "pyndoc" / "filter.py").resolve()
    if sys.platform != "win32" and filter_file.exists():
        if not (filter_file.stat().st_mode & 0o111):
            try:
                filter_file.chmod(filter_file.stat().st_mode | 0o755)
            except OSError as e:
                logger.warning(
                    "Could not set executable permission on %s: %s", filter_file, e
                )

    page_path = page.file.src_uri if page and page.file else ""

    for div in example_divs:
        classes = div.get("class", [])
        raises_exception = "raises-exception" in classes

        # Extract optional title from superfences filename span
        filename_span = div.find("span", class_="filename")
        title: str | None = None
        if filename_span:
            title = filename_span.get_text().strip()
            filename_span.decompose()

        # Extract raw code
        code_elem = div.find("code")
        raw_markdown = code_elem.get_text() if code_elem else ""

        # Render with Pyndoc
        rendered_html, is_error = _render_example_to_html(
            raw_markdown,
            filter_file,
            raises_exception=raises_exception,
            page_path=page_path,
        )

        preview_soup = BeautifulSoup(rendered_html, "html.parser")
        # Ensure any Pandoc math spans also have arithmatex class for MathJax
        # and replace conflicting 'inline' class with 'math-inline' to prevent Material from floating it
        for math_span in preview_soup.find_all("span", class_="math"):
            existing = math_span.get("class", [])
            new_classes = [c if c != "inline" else "math-inline" for c in existing]
            if "arithmatex" not in new_classes:
                new_classes.append("arithmatex")
            math_span["class"] = new_classes

        # Build outer unified container
        container_classes = ["pyndoc-example"]
        if raises_exception:
            container_classes.append("raises-exception")
        container = soup.new_tag("div", attrs={"class": " ".join(container_classes)})

        # Header bar if title was supplied
        if title:
            header = soup.new_tag("div", attrs={"class": "pyndoc-example-header"})
            title_span = soup.new_tag("span", attrs={"class": "pyndoc-example-title"})
            title_span.string = title
            badge = soup.new_tag("span", attrs={"class": "pyndoc-example-badge"})
            badge.string = "Example"
            header.append(title_span)
            header.append(badge)
            container.append(header)

        # Source code block (retain highlight classes except example tags)
        source_container = soup.new_tag("div", attrs={"class": "pyndoc-example-source"})
        div_classes = [c for c in classes if c not in ("example", "raises-exception")]
        div["class"] = div_classes
        div.wrap(source_container)
        source_container.wrap(container)

        # Divider with Result label
        divider = soup.new_tag("div", attrs={"class": "pyndoc-example-divider"})
        divider_label = soup.new_tag("span", attrs={"class": "pyndoc-example-divider-label"})
        divider_label.string = "Result"
        divider.append(divider_label)
        container.append(divider)

        # Result preview section
        preview_container = soup.new_tag(
            "div", attrs={"class": "pyndoc-example-preview md-typeset"}
        )
        for child in list(preview_soup.children):
            preview_container.append(child)
        container.append(preview_container)

    # Protect any other Pandoc inline math across the document from Material's `.inline` float rule
    for math_elem in soup.find_all("span", class_="math"):
        existing = math_elem.get("class", [])
        if "inline" in existing:
            math_elem["class"] = [
                c if c != "inline" else "math-inline" for c in existing
            ]
            if "arithmatex" not in math_elem["class"]:
                math_elem["class"].append("arithmatex")

    return str(soup)
