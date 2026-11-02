from __future__ import annotations

import importlib
import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup
from mkdocs.utils import get_relative_url

# Ensure local source tree takes precedence
_SRC_DIR = str(Path(__file__).resolve().parent.parent.parent / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page

IDENTIFIER_REGEX = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*(?:\(\))?$"
)

# Mapping of module path to its documentation page path in the site
MODULE_PAGE_MAP: dict[str, str] = {
    "pyndoc.__main__": "api/cli/",
    "pyndoc.preprocess": "api/preprocess/",
    "pyndoc.filter": "api/filter/",
    "pyndoc.formats": "api/formats/",
    "pyndoc.timer": "api/timer/",
    "pyndoc.latex.core": "api/latex/core/",
    "pyndoc.latex.quantity": "api/latex/quantity/",
    "pyndoc.latex.dsl": "api/latex/dsl/",
    "pyndoc.latex.containers": "api/latex/containers/",
    "pyndoc.latex.functions": "api/latex/functions/",
    "pyndoc.latex.calculus": "api/latex/calculus/",
    "pyndoc.latex.typography": "api/latex/typography/",
    "pyndoc.latex.symbols": "api/latex/symbols/",
    "pyndoc.latex.config": "api/latex/config/",
    "pyndoc.latex.units": "api/latex/units/",
    "pyndoc.markdown.tables": "api/markdown/tables/",
    "pyndoc.markdown.lists": "api/markdown/lists/",
    "pyndoc.markdown.blocks": "api/markdown/blocks/",
    "pyndoc.markdown.inlines": "api/markdown/inlines/",
    "pyndoc.markdown.coercion": "api/markdown/coercion/",
    "pyndoc.markdown.convert": "api/markdown/convert/",
}

TOPIC_PAGE_MAP: dict[str, str] = {
    "pyndoc": "api/",
    "pyndoc.latex": "api/latex/",
    "pyndoc.markdown": "api/markdown/",
}

PAGE_DEFAULT_PARENTS: dict[str, list[str]] = {
    "api/formats.md": ["Format"],
    "api/timer.md": ["Timer"],
    "api/latex/core.md": ["Token", "Literal", "DimensionedLiteral"],
    "api/latex/quantity.md": ["Quantity", "Variable"],
    "api/latex/config.md": ["LatexConfig"],
    "api/latex/containers.md": [
        "Bracket",
        "SquareBracket",
        "CurlyBracket",
        "AngleBracket",
        "AbsoluteValue",
        "Norm",
        "Floor",
        "Ceil",
        "MixedBracket",
        "ArrayIndex",
    ],
    "api/latex/functions.md": [
        "Function",
        "Operator",
        "FunctionGenerator",
        "OperatorGenerator",
    ],
    "api/latex/calculus.md": [
        "Derivative",
        "PartialDerivative",
        "Integral",
        "ContourIntegral",
        "Limit",
        "Summation",
        "Product",
    ],
    "api/markdown/tables.md": ["Alignment"],
    "api/markdown/lists.md": ["Enumeration", "ListDelimiter"],
    "api/markdown/coercion.md": [
        "PanfluteError",
        "PanfluteTypeError",
        "PanfluteValueError",
    ],
    "user-guide/math-typesetting.md": ["Quantity", "Variable", "LatexConfig"],
    "user-guide/markdown-ast.md": ["Alignment", "Enumeration", "ListDelimiter"],
}


@dataclass
class SymbolEntry:
    name: str
    full_name: str
    anchor: str
    page_path: str
    parent: str | None = None
    is_class: bool = False


def _build_symbol_index() -> dict[str, list[SymbolEntry]]:
    index: dict[str, list[SymbolEntry]] = {}

    def add_entry(key: str, entry: SymbolEntry) -> None:
        index.setdefault(key, []).append(entry)

    # Discover parent packages for re-export resolution
    parent_packages: list[Any] = []
    for pkg_name in ["pyndoc", "pyndoc.latex", "pyndoc.markdown"]:
        try:
            parent_packages.append(importlib.import_module(pkg_name))
        except Exception:
            pass

    # 1. Documented modules and their members
    for mod_name, page_path in MODULE_PAGE_MAP.items():
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue

        mod_parts = mod_name.split(".")
        allowed_members = set(getattr(mod, "__all__", []))
        has_all = bool(allowed_members)

        for name, obj in inspect.getmembers(mod):
            if name.startswith("_"):
                continue
            if has_all and name not in allowed_members:
                continue

            if inspect.isclass(obj) and obj.__module__ == mod_name:
                c_anchor = f"{mod_name}.{name}"
                c_entry = SymbolEntry(
                    name=name,
                    full_name=c_anchor,
                    anchor=c_anchor,
                    page_path=page_path,
                    is_class=True,
                )
                class_keys = {name, f"{mod_name}.{name}"}
                if len(mod_parts) > 1:
                    class_keys.add(f"{mod_parts[-1]}.{name}")
                if len(mod_parts) > 2:
                    class_keys.add(f"{'.'.join(mod_parts[1:])}.{name}")

                for parent_pkg in parent_packages:
                    if getattr(parent_pkg, name, None) is obj:
                        pkg_name = parent_pkg.__name__
                        class_keys.add(f"{pkg_name}.{name}")
                        short_pkg = pkg_name.split(".")[-1]
                        if short_pkg != pkg_name:
                            class_keys.add(f"{short_pkg}.{name}")

                for k in class_keys:
                    add_entry(k, c_entry)

                # Class members (methods, properties, class attributes)
                class_attributes = set(obj.__dict__.keys()) | set(
                    getattr(obj, "__annotations__", {}).keys()
                )
                for m_name in class_attributes:
                    if m_name.startswith("_"):
                        continue
                    m_anchor = f"{c_anchor}.{m_name}"
                    m_entry = SymbolEntry(
                        name=m_name,
                        full_name=f"{name}.{m_name}",
                        anchor=m_anchor,
                        page_path=page_path,
                        parent=name,
                    )
                    add_entry(m_name, m_entry)
                    for k in class_keys:
                        add_entry(f"{k}.{m_name}", m_entry)

            elif inspect.isfunction(obj) and obj.__module__ == mod_name:
                f_anchor = f"{mod_name}.{name}"
                f_entry = SymbolEntry(
                    name=name,
                    full_name=f_anchor,
                    anchor=f_anchor,
                    page_path=page_path,
                )
                fn_keys = {name, f"{mod_name}.{name}"}
                if len(mod_parts) > 1:
                    fn_keys.add(f"{mod_parts[-1]}.{name}")
                if len(mod_parts) > 2:
                    fn_keys.add(f"{'.'.join(mod_parts[1:])}.{name}")

                for parent_pkg in parent_packages:
                    if getattr(parent_pkg, name, None) is obj:
                        pkg_name = parent_pkg.__name__
                        fn_keys.add(f"{pkg_name}.{name}")
                        short_pkg = pkg_name.split(".")[-1]
                        if short_pkg != pkg_name:
                            fn_keys.add(f"{short_pkg}.{name}")

                for k in fn_keys:
                    add_entry(k, f_entry)

    # 2. Topic & module overview pages
    all_modules = {**TOPIC_PAGE_MAP, **MODULE_PAGE_MAP}
    for mod_name, page_path in all_modules.items():
        entry = SymbolEntry(
            name=mod_name,
            full_name=mod_name,
            anchor="",
            page_path=page_path,
        )
        add_entry(mod_name, entry)
        parts = mod_name.split(".")
        if len(parts) > 1:
            short_mod = ".".join(parts[1:])
            # Only add short module name if not already occupied by an exact symbol name
            if short_mod not in index:
                add_entry(short_mod, entry)

    return index


_SYMBOL_INDEX: dict[str, list[SymbolEntry]] | None = None


def get_symbol_index() -> dict[str, list[SymbolEntry]]:
    global _SYMBOL_INDEX
    if _SYMBOL_INDEX is None:
        _SYMBOL_INDEX = _build_symbol_index()
    return _SYMBOL_INDEX


def _make_relative_url(
    target_page_path: str, anchor: str, current_page_url: str
) -> str:
    target = target_page_path.strip("/")
    current = current_page_url.strip("/")

    if target == current:
        return f"#{anchor}" if anchor else "#"

    rel = get_relative_url(target_page_path, current_page_url)
    if anchor:
        if rel in (".", "./"):
            return f"#{anchor}"
        elif rel.endswith("/"):
            return f"{rel}#{anchor}"
        else:
            return f"{rel}/#{anchor}"
    return rel


def log_ambiguity_warning(message: str) -> None:
    print(f"\033[33mWARNING  -  autolink: {message}\033[0m", file=sys.stderr)


def on_page_content(
    html: str, page: Page, config: MkDocsConfig, files: Files, **kwargs: Any
) -> str:
    index = get_symbol_index()

    soup = BeautifulSoup(html, "html.parser")

    # Context of previously linked parent objects on this page
    src_uri = page.file.src_uri if page.file else ""
    linked_context: list[str] = list(PAGE_DEFAULT_PARENTS.get(src_uri, []))

    page_url = page.url or ""

    for code in soup.find_all("code"):
        # 1. Skip if inside a code block
        if code.find_parent("pre"):
            continue

        # 2. Skip if already inside a link
        if code.find_parent("a"):
            continue

        # 3. Skip if inside a heading (preserves TOC anchors and permalinks)
        if code.find_parent(re.compile(r"^h[1-6]$")):
            h_text = code.get_text().strip()
            h_lookup = h_text[:-2] if h_text.endswith("()") else h_text
            h_cands = index.get(h_lookup)
            if h_cands and any(c.is_class for c in h_cands):
                if not linked_context or linked_context[-1] != h_lookup:
                    linked_context.append(h_lookup)
            continue

        # In mkdocstrings output, code may reside within a doc-class container
        doc_class = code.find_parent("div", class_="doc-class")
        if doc_class:
            class_name_span = doc_class.find("span", class_="doc-class-name")
            if class_name_span:
                current_class = class_name_span.get_text().strip()
                if not linked_context or linked_context[-1] != current_class:
                    linked_context.append(current_class)

        # 4. Check text content
        raw_text = code.get_text().strip()
        if not raw_text or not IDENTIFIER_REGEX.match(raw_text):
            continue

        # Strip trailing () if present for lookup
        has_parens = raw_text.endswith("()")
        lookup_name = raw_text[:-2] if has_parens else raw_text

        candidates = index.get(lookup_name)
        if not candidates:
            continue

        chosen_entry: SymbolEntry | None = None

        if len(candidates) == 1:
            # Unambiguous
            chosen_entry = candidates[0]
        else:
            # Ambiguity resolution
            # Strategy A: If syntax had parentheses (func()) or if one candidate is a symbol
            # and another is a module/topic page (anchor=""), prefer the symbol with an anchor.
            if has_parens:
                with_anchor = [c for c in candidates if c.anchor]
                if len(with_anchor) == 1:
                    chosen_entry = with_anchor[0]
            elif any(c.anchor == "" for c in candidates) and any(c.anchor != "" for c in candidates):
                # If no parens and candidates include a module overview with exact match
                if any(c.name == lookup_name and c.anchor == "" for c in candidates):
                    topic_matches = [c for c in candidates if c.name == lookup_name and c.anchor == ""]
                    if len(topic_matches) == 1:
                        chosen_entry = topic_matches[0]

            # Strategy B: Prefer candidate on current page if applicable
            if chosen_entry is None:
                page_matches = [
                    c for c in candidates if c.page_path.strip("/") == page_url.strip("/")
                ]
                if len(page_matches) == 1:
                    chosen_entry = page_matches[0]

            # Strategy C: Walk backwards through previously-linked parents
            if chosen_entry is None:
                matching_parent: str | None = None
                for prev_parent in reversed(linked_context):
                    for cand in candidates:
                        if cand.parent == prev_parent:
                            chosen_entry = cand
                            matching_parent = prev_parent
                            break
                    if chosen_entry is not None:
                        break

            # Strategy D: Submodule contextual preference based on page path
            if chosen_entry is None:
                if src_uri.startswith("api/latex/") or "math" in src_uri:
                    tex_cands = [c for c in candidates if "latex" in c.page_path]
                    if len(tex_cands) == 1:
                        chosen_entry = tex_cands[0]
                elif src_uri.startswith("api/markdown/") or "markdown" in src_uri:
                    md_cands = [c for c in candidates if "markdown" in c.page_path]
                    if len(md_cands) == 1:
                        chosen_entry = md_cands[0]

            if chosen_entry is None:
                # If still ambiguous, skip linking
                continue

        # Build relative link
        target_href = _make_relative_url(
            chosen_entry.page_path, chosen_entry.anchor, page_url
        )

        title_attr = chosen_entry.full_name or chosen_entry.anchor or None
        link_attrs: dict[str, str] = {
            "href": target_href,
            "class": "autorefs autorefs-internal",
        }
        if title_attr:
            link_attrs["title"] = title_attr

        link_tag = soup.new_tag("a", **link_attrs)
        code.wrap(link_tag)

        # Record context for subsequent lookups
        if chosen_entry.parent:
            linked_context.append(chosen_entry.parent)
        if chosen_entry.is_class:
            linked_context.append(chosen_entry.name)

    return str(soup)
