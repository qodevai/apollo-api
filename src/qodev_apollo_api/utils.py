"""Utility functions for Apollo client.

Includes ProseMirror JSON <-> Markdown conversion for notes.
"""

import json
import re

_ORDERED_ITEM_RE = re.compile(r"^\d+\.\s+(.*)$")


def prosemirror_to_markdown(content_json: str) -> tuple[str, str]:
    """Convert ProseMirror JSON content to Markdown.

    Args:
        content_json: ProseMirror JSON string from Apollo notes

    Returns:
        Tuple of (title, markdown_content)
    """
    if not content_json:
        return "Untitled", ""

    try:
        doc = json.loads(content_json)
    except json.JSONDecodeError:
        return "Untitled", content_json  # Return raw if not valid JSON

    if not isinstance(doc, dict) or doc.get("type") != "doc":
        return "Untitled", content_json

    content = doc.get("content", [])
    if not content:
        return "Untitled", ""

    title = "Untitled"
    lines = []

    for node in content:
        node_type = node.get("type")

        if node_type == "noteTitle":
            # Extract title
            title = _extract_text(node)

        elif node_type == "paragraph":
            # Extract paragraph text
            text = _extract_text(node)
            if text:
                lines.append(text)

        elif node_type == "bulletList":
            # Extract bullet list
            for item in node.get("content", []):
                if item.get("type") == "listItem":
                    item_text = _extract_text_from_list_item(item)
                    if item_text:
                        lines.append(f"- {item_text}")

        elif node_type == "orderedList":
            # Extract ordered list
            for idx, item in enumerate(node.get("content", []), 1):
                if item.get("type") == "listItem":
                    item_text = _extract_text_from_list_item(item)
                    if item_text:
                        lines.append(f"{idx}. {item_text}")

    markdown = "\n\n".join(lines)
    return title, markdown


def _extract_text(node: dict) -> str:
    """Extract plain text from a ProseMirror node."""
    content = node.get("content", [])
    if not content:
        return ""

    text_parts = []
    for item in content:
        if item.get("type") == "text":
            text_parts.append(item.get("text", ""))
        elif item.get("type") == "hardBreak":
            text_parts.append("\n")
        else:
            # Recursively extract from nested content
            nested_text = _extract_text(item)
            if nested_text:
                text_parts.append(nested_text)

    return "".join(text_parts)


def _extract_text_from_list_item(item: dict) -> str:
    """Extract text from a list item, which may contain paragraphs."""
    content = item.get("content", [])
    if not content:
        return ""

    text_parts = []
    for node in content:
        if node.get("type") == "paragraph":
            text = _extract_text(node)
            if text:
                text_parts.append(text)

    return " ".join(text_parts)


def markdown_to_prosemirror(content: str, title: str | None = None) -> str:
    """Convert plain text / lightweight Markdown to a ProseMirror JSON string.

    Apollo's ``POST /notes`` stores the note body in the ``content`` field as a
    ProseMirror JSON string; this is the inverse of :func:`prosemirror_to_markdown`
    for the node types Apollo notes use.

    Supports:
      * an optional note title (``noteTitle`` node)
      * paragraphs (one per line; blank lines become empty paragraphs)
      * bullet lists (lines starting with ``- `` or ``* ``)
      * ordered lists (lines starting with ``1. ``)

    Args:
        content: Note body as plain text / Markdown.
        title: Optional note title (rendered as the ProseMirror ``noteTitle``).

    Returns:
        ProseMirror document as a JSON string, ready to post to ``content``.
    """
    nodes: list[dict] = []
    if title:
        nodes.append({"type": "noteTitle", "content": [{"type": "text", "text": title}]})

    def _paragraph(text: str) -> dict:
        # Empty text nodes are invalid in ProseMirror — emit a bare paragraph.
        if not text:
            return {"type": "paragraph"}
        return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

    def _list_item(text: str) -> dict:
        return {"type": "listItem", "content": [_paragraph(text)]}

    lines = (content or "").split("\n")
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped[:2] in ("- ", "* "):
            items = []
            while i < len(lines) and lines[i].strip()[:2] in ("- ", "* "):
                items.append(_list_item(lines[i].strip()[2:].strip()))
                i += 1
            nodes.append({"type": "bulletList", "content": items})
            continue

        if _ORDERED_ITEM_RE.match(stripped):
            items = []
            while i < len(lines) and (m := _ORDERED_ITEM_RE.match(lines[i].strip())):
                items.append(_list_item(m.group(1).strip()))
                i += 1
            nodes.append({"type": "orderedList", "content": items})
            continue

        nodes.append(_paragraph(lines[i]))
        i += 1

    return json.dumps({"type": "doc", "content": nodes}, ensure_ascii=False)


def normalize_linkedin_url(url: str) -> str:
    """Normalize LinkedIn URL for comparison.

    Args:
        url: LinkedIn profile URL

    Returns:
        Normalized URL (lowercase, stripped, trailing slash removed)
    """
    if not url:
        return ""
    url = url.lower().strip().rstrip("/")
    # Normalize scheme to https://
    if url.startswith("http://"):
        url = "https://" + url[7:]
    elif not url.startswith("https://"):
        url = f"https://{url}"
    return url
