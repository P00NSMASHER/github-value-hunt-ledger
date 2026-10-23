"""Render the approved RETALLY wordmark only in short, visible brand text.

This is a presentation transform. Keep metadata, legal prose, options, inputs,
button values, script payloads, email URLs and programmatic names as real text.
"""
from __future__ import annotations

from html import escape
import re

TOKENS = re.compile(r"(<!--.*?-->|<![^>]*>|</?[a-zA-Z][^>]*>)", re.DOTALL)
TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z][\w:-]*)\b")
WORD = re.compile(r"(?<![\w])RETALLY(?![\w])", re.IGNORECASE)
VOID = frozenset(("area", "base", "br", "col", "embed", "hr", "img",
                  "input", "link", "meta", "param", "source", "track", "wbr"))
BLOCKED = frozenset(("head", "title", "script", "style", "svg", "select",
                     "option", "textarea", "button", "label", "noscript",
                     "code", "pre"))
DISPLAY = frozenset(("a", "span", "small", "strong", "b", "h1", "h2", "h3", "h4", "h5", "h6"))
INLINE = frozenset(("p", "div"))


def embed_approved_wordmark(markup: str, asset_path: str) -> str:
    """Swap short, visible brand words without parsing or altering link attributes.

    Intentional narrow scope: paragraphs over 100 characters, legal footer notes,
    form text, and script/JSON-LD keep ordinary text to preserve readability and
    machine contracts. One shared cached first-party master is reused on a page.
    """
    if not asset_path.startswith("/") and not asset_path.startswith("assets/"):
        raise ValueError("Wordmark must be a first-party, relative asset")
    picture = (
        '<img class="retally-wordmark" src="' + escape(asset_path, quote=True)
        + '" alt="RETALLY" width="1619" height="257" decoding="async">'
    )
    in_body = False
    stack: list[str] = []
    output: list[str] = []
    for token in TOKENS.split(markup):
        if not token:
            continue
        if token.startswith("<"):
            match = TAG.match(token)
            if match:
                closing, tag = match.groups()
                tag = tag.lower()
                if closing:
                    if tag in stack:
                        stack = stack[:len(stack) - 1 - stack[::-1].index(tag)]
                    if tag == "body":
                        in_body = False
                else:
                    if tag == "body":
                        in_body = True
                    if tag not in VOID and not token.rstrip().endswith("/>"):
                        stack.append(tag)
            output.append(token)
            continue
        if not in_body or not WORD.search(token) or not stack:
            output.append(token)
            continue
        if any(tag in BLOCKED for tag in stack):
            output.append(token)
            continue
        parent = stack[-1]
        if parent in DISPLAY:
            output.append(WORD.sub(picture, token))
        elif (parent in INLINE and len(token.strip()) <= 100
              and "©" not in token and "&copy;" not in token):
            output.append(WORD.sub(picture, token))
        else:
            output.append(token)
    return "".join(output)
