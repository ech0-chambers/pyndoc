from __future__ import annotations

import html as html_lib
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup
from bs4.element import Tag
from mkdocs.plugins import get_plugin_logger
import panflute

# Ensure local source tree takes precedence
_SRC_DIR = str(Path(__file__).resolve().parent.parent.parent / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from pyndoc.preprocess import deindent, no_console, preprocess  # noqa: E402

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

# Regex to match code fence openings tagged with .quiet or .silent
QUIET_SILENT_FENCE_REGEX = re.compile(
    r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})[ \t]*(?:(?P<lang>[a-zA-Z0-9_+-]+)[ \t]+)?(?:"
    r"\{\s*(?P<attrs>[^}]*\.(?:quiet|silent)\b[^}]*)\}"
    r"|\.(?P<dot_tag>quiet|silent)\b(?P<attrs2>[^\n]*)"
    r"|(?P<bare_tag>quiet|silent)\b(?P<attrs3>[^\n]*)"
    r")[ \t]*$",
    re.MULTILINE,
)


def on_page_markdown(
    markdown: str, page: Page, config: MkDocsConfig, files: Files, **kwargs: Any
) -> str:
    """Normalize example, quiet, and silent code fences to standard superfences format."""

    def _replace_example_fence(m: re.Match[str]) -> str:
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

    def _replace_quiet_silent_fence(m: re.Match[str]) -> str:
        indent = m.group("indent")
        fence = m.group("fence")
        lang = m.group("lang") or "python"
        if m.group("attrs") is not None:
            attrs = m.group("attrs").strip()
            return f"{indent}{fence}{lang} {{{attrs}}}"
        tag = m.group("dot_tag") or m.group("bare_tag")
        attrs_extra = (m.group("attrs2") or m.group("attrs3") or "").strip()
        extra_str = f" {attrs_extra}" if attrs_extra else ""
        return f"{indent}{fence}{lang} {{.{tag}{extra_str}}}"

    text = EXAMPLE_FENCE_REGEX.sub(_replace_example_fence, markdown)
    return QUIET_SILENT_FENCE_REGEX.sub(_replace_quiet_silent_fence, text)


def _render_example_to_html(
    raw_markdown: str,
    filter_file: Path,
    raises_exception: bool = False,
    page_path: str = "",
    setup_code: str = "",
    is_inline: bool = False,
) -> tuple[str, bool]:
    """Execute Pyndoc preprocessing and Pandoc conversion on raw Markdown.

    When `raises_exception` is True, intentional errors are converted as normal
    without logging warnings or triggering error UI blocks.
    When `setup_code` is provided, it is prepended as a quiet Python block so
    document context is available in the filter execution environment.
    """
    if not raw_markdown.strip():
        return ("", False)

    input_markdown = raw_markdown
    if is_inline:
        # Prevent solitary inline macros (e.g. `%%q()`) from being promoted to block fences
        input_markdown = f"<!-- inline -->{raw_markdown}"

    if setup_code.strip():
        input_markdown = f"```{{.py .quiet}}\n{setup_code.strip()}\n```\n\n{input_markdown}"

    try:
        # Pass a silenced console to prevent rich terminal output during docs builds
        preprocessed = preprocess(
            input_markdown, target_format="html", console=no_console()
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


def _get_admonition_context(tag: Tag) -> tuple[bool, bool, bool]:
    """Check if tag is within an example admonition and if it is first and/or last content child.

    Returns:
        tuple of (in_admonition, is_first, is_last)
    """
    admonition = tag.find_parent(
        lambda el: el and el.name in ("div", "details") and (
            "admonition" in el.get("class", []) or el.name == "details"
        )
    )
    if not admonition or "example" not in admonition.get("class", []):
        return False, False, False

    # Find the top-level branch child within the admonition containing this tag
    current = tag
    while current.parent and current.parent is not admonition:
        current = current.parent

    content_children = [
        child
        for child in admonition.children
        if isinstance(child, Tag)
        and not (
            (child.name == "p" and "admonition-title" in child.get("class", []))
            or child.name == "summary"
        )
    ]
    if not content_children:
        return True, True, True

    is_first = (content_children[0] is current)
    is_last = (content_children[-1] is current)

    # If tag is nested within an intermediate container, check siblings within that parent
    if current is not tag and tag.parent:
        siblings = [c for c in tag.parent.children if isinstance(c, Tag)]
        if siblings and siblings[0] is not tag:
            is_first = False
        if siblings and siblings[-1] is not tag:
            is_last = False

    return True, is_first, is_last


def on_page_content(
    html: str, page: Page, config: MkDocsConfig, files: Files, **kwargs: Any
) -> str:
    """Transform example code blocks into unified source + live preview boxes,
    execute .quiet and .silent code blocks in document context, and format
    inline example codes into horizontal preview spans."""
    if "example" not in html and "quiet" not in html and "silent" not in html:
        return html

    soup = BeautifulSoup(html, "html.parser")

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
    accumulated_context: list[str] = []

    # Find candidate elements in document order
    def is_candidate(tag: Tag) -> bool:
        if tag.name == "div":
            classes = tag.get("class", [])
            if "example" in classes and "highlight" in classes:
                return True
            if "quiet" in classes or "silent" in classes:
                return True
        elif tag.name == "code":
            if "example" in tag.get("class", []) and tag.parent and tag.parent.name != "pre":
                return True
        return False

    candidates = soup.find_all(is_candidate)
    if not candidates:
        return html

    for tag in candidates:
        # Skip tags inside already created unified containers or already decomposed
        if getattr(tag, "decomposed", False) or tag.parent is None:
            continue
        if tag.find_parent(class_="pyndoc-example"):
            continue

        if tag.name == "div":
            classes = tag.get("class", [])
            if "example" in classes and "highlight" in classes:
                # Block example
                raises_exception = "raises-exception" in classes

                # Extract optional title from superfences filename span
                filename_span = tag.find("span", class_="filename")
                title: str | None = None
                if filename_span:
                    title = filename_span.get_text().strip()
                    filename_span.decompose()

                code_elem = tag.find("code")
                raw_markdown = code_elem.get_text() if code_elem else ""

                # Render with Pyndoc
                rendered_html, is_error = _render_example_to_html(
                    raw_markdown,
                    filter_file,
                    raises_exception=raises_exception,
                    page_path=page_path,
                    setup_code="\n\n".join(accumulated_context),
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

                in_adm, is_first, is_last = _get_admonition_context(tag)
                if in_adm:
                    container_classes.append("in-admonition")
                    if is_first:
                        container_classes.append("is-first")
                    if is_last:
                        container_classes.append("is-last")

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
                tag["class"] = div_classes
                tag.wrap(source_container)
                source_container.wrap(container)

                # Divider with Result label
                divider = soup.new_tag("div", attrs={"class": "pyndoc-example-divider"})
                divider_label = soup.new_tag(
                    "span", attrs={"class": "pyndoc-example-divider-label"}
                )
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

            elif "quiet" in classes:
                code_elem = tag.find("code")
                if code_elem:
                    accumulated_context.append(deindent(code_elem.get_text()).strip())
                # Left in document as a formatted code block as normal
                tag["class"] = [c for c in classes if c != "quiet"]

            elif "silent" in classes:
                code_elem = tag.find("code")
                if code_elem:
                    accumulated_context.append(deindent(code_elem.get_text()).strip())
                # Removed from document
                tag.decompose()

        elif tag.name == "code":
            # Inline example: rendered as Markdown through Pyndoc pipeline
            classes = tag.get("class", [])
            raises_exception = "raises-exception" in classes
            raw_markdown = tag.get_text()

            rendered_html, is_error = _render_example_to_html(
                raw_markdown,
                filter_file,
                raises_exception=raises_exception,
                page_path=page_path,
                setup_code="\n".join(accumulated_context),
                is_inline=True,
            )

            preview_soup = BeautifulSoup(rendered_html, "html.parser")
            # Update math classes for MathJax
            for math_span in preview_soup.find_all("span", class_="math"):
                existing = math_span.get("class", [])
                new_classes = [c if c != "inline" else "math-inline" for c in existing]
                if "arithmatex" not in new_classes:
                    new_classes.append("arithmatex")
                math_span["class"] = new_classes

            # Convert block elements to inline elements
            for p in preview_soup.find_all("p"):
                p.unwrap()
            for pre in preview_soup.find_all("pre"):
                pre.unwrap()
            for div in preview_soup.find_all("div"):
                div.name = "span"
                if "pyndoc-example-error" in div.get("class", []):
                    div["class"] = ["pyndoc-inline-error"]
            for code in preview_soup.find_all("code"):
                if raises_exception:
                    code["class"] = ["pyndoc-inline-error"]

            container_classes = ["pyndoc-inline-example"]
            if raises_exception:
                container_classes.append("raises-exception")
            for c in classes:
                if (
                    c not in ("example", "raises-exception", "pyndoc-inline-example")
                    and c not in container_classes
                ):
                    container_classes.append(c)

            container = soup.new_tag("span", attrs={"class": " ".join(container_classes)})

            source_code = soup.new_tag("code", attrs={"class": "pyndoc-inline-source"})
            source_code.string = raw_markdown.strip()
            container.append(source_code)

            arrow_span = soup.new_tag("span", attrs={"class": "pyndoc-inline-arrow"})
            arrow_span.string = "→"
            container.append(arrow_span)

            result_span = soup.new_tag("span", attrs={"class": "pyndoc-inline-result"})
            for child in list(preview_soup.children):
                result_span.append(child)
            container.append(result_span)

            tag.replace_with(container)

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
