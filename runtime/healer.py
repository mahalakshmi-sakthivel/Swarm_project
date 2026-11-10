"""
HTML Parser-Based Markup Healer for Stage 2 Swarm (Phase 6).
Ensures small 4B LLM outputs have properly balanced and closed HTML tags.
Uses Python's standard library html.parser with zero external dependencies.
"""

from html.parser import HTMLParser
import re
from typing import List, Optional, Tuple

# HTML5 void elements that do not require closing tags
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "param", "source", "track", "wbr"
}


class HTMLTagHealer(HTMLParser):
    """
    Stateful parser that traverses HTML tokens, tracks open tag hierarchy,
    and automatically balances and closes unclosed tags in LIFO order.
    """
    def __init__(self):
        super().__init__()
        self.stack: List[str] = []
        self.output: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        tag_lower = tag.lower()
        attr_parts = []
        for k, v in attrs:
            if v is None:
                attr_parts.append(f" {k}")
            else:
                attr_parts.append(f' {k}="{v}"')
        attr_str = "".join(attr_parts)

        self.output.append(f"<{tag}{attr_str}>")
        if tag_lower not in VOID_TAGS:
            self.stack.append(tag_lower)

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in VOID_TAGS:
            return

        # If tag is in stack, close all intermediate unclosed tags up to this tag
        if tag_lower in self.stack:
            while self.stack:
                popped = self.stack.pop()
                self.output.append(f"</{popped}>")
                if popped == tag_lower:
                    break

    def handle_data(self, data: str):
        self.output.append(data)

    def handle_comment(self, data: str):
        self.output.append(f"<!--{data}-->")

    def handle_decl(self, decl: str):
        self.output.append(f"<!{decl}>")

    def handle_entityref(self, name: str):
        self.output.append(f"&{name};")

    def handle_charref(self, name: str):
        self.output.append(f"&#{name};")

    def get_healed_html(self) -> str:
        self.close()
        # Automatically close any remaining open tags in reverse order
        while self.stack:
            popped = self.stack.pop()
            self.output.append(f"</{popped}>")
        return "".join(self.output)


def heal_html_markup(raw_html: str) -> str:
    """
    Validates and repairs unbalanced or unclosed HTML tags in raw_html.
    Guarantees that every opening tag (like <section>, <div>, <p>, <h3>) has a matching closing tag.
    Preserves void tags (<img>, <input>, <br>, <meta>, <link>) without erroneous closures.
    """
    if not raw_html or not raw_html.strip():
        return raw_html

    try:
        healer = HTMLTagHealer()
        healer.feed(raw_html)
        return healer.get_healed_html()
    except Exception:
        # If parsing encounters unrecoverable structural syntax errors, return original
        return raw_html
