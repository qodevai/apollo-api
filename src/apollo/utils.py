"""Utility functions for Apollo client.

Includes ProseMirror JSON to Markdown conversion for notes.
"""

import json


def prosemirror_to_markdown(content_json: str) -> tuple[str, str]:
    """Convert ProseMirror JSON content to Markdown.

    Args:
        content_json: ProseMirror JSON string from Apollo notes

    Returns:
        Tuple of (title, markdown_content)
    """
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
    # Ensure it starts with http:// or https://
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url
