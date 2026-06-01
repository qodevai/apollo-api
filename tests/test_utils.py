"""Tests for Apollo utility functions."""

import json

from qodev_apollo_api.utils import (
    markdown_to_prosemirror,
    normalize_linkedin_url,
    prosemirror_to_markdown,
)


def test_prosemirror_to_markdown_simple():
    """Test basic ProseMirror to Markdown conversion."""
    prosemirror_json = json.dumps(
        {
            "type": "doc",
            "content": [
                {"type": "noteTitle", "content": [{"type": "text", "text": "Test Title"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "Test paragraph"}]},
            ],
        }
    )

    title, markdown = prosemirror_to_markdown(prosemirror_json)
    assert title == "Test Title"
    assert markdown == "Test paragraph"


def test_prosemirror_to_markdown_with_lists():
    """Test ProseMirror conversion with bullet lists."""
    prosemirror_json = json.dumps(
        {
            "type": "doc",
            "content": [
                {"type": "noteTitle", "content": [{"type": "text", "text": "Notes"}]},
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "First item"}],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Second item"}],
                                }
                            ],
                        },
                    ],
                },
            ],
        }
    )

    title, markdown = prosemirror_to_markdown(prosemirror_json)
    assert title == "Notes"
    assert "- First item" in markdown
    assert "- Second item" in markdown


def test_prosemirror_invalid_json():
    """Test handling of invalid JSON."""
    title, markdown = prosemirror_to_markdown("not valid json")
    assert title == "Untitled"
    assert markdown == "not valid json"


def test_prosemirror_empty_doc():
    """Test handling of empty document."""
    prosemirror_json = json.dumps({"type": "doc", "content": []})
    title, markdown = prosemirror_to_markdown(prosemirror_json)
    assert title == "Untitled"
    assert markdown == ""


def test_normalize_linkedin_url():
    """Test LinkedIn URL normalization."""
    # Test basic normalization
    assert (
        normalize_linkedin_url("https://linkedin.com/in/johndoe")
        == "https://linkedin.com/in/johndoe"
    )

    # Test lowercase conversion
    assert (
        normalize_linkedin_url("HTTPS://LinkedIn.com/in/JohnDoe")
        == "https://linkedin.com/in/johndoe"
    )

    # Test trailing slash removal
    assert (
        normalize_linkedin_url("https://linkedin.com/in/johndoe/")
        == "https://linkedin.com/in/johndoe"
    )

    # Test protocol addition
    assert normalize_linkedin_url("linkedin.com/in/johndoe") == "https://linkedin.com/in/johndoe"

    # Test whitespace handling
    assert (
        normalize_linkedin_url("  https://linkedin.com/in/johndoe  ")
        == "https://linkedin.com/in/johndoe"
    )


def test_normalize_linkedin_url_empty():
    """Test normalization of empty URL."""
    assert normalize_linkedin_url("") == ""
    assert normalize_linkedin_url(None) == ""


def test_markdown_to_prosemirror_simple():
    """Title + body become a noteTitle node and a paragraph node."""
    doc = json.loads(markdown_to_prosemirror("Hello world", title="My Title"))
    assert doc["type"] == "doc"
    assert doc["content"][0] == {
        "type": "noteTitle",
        "content": [{"type": "text", "text": "My Title"}],
    }
    assert doc["content"][1] == {
        "type": "paragraph",
        "content": [{"type": "text", "text": "Hello world"}],
    }


def test_markdown_to_prosemirror_blank_line_is_empty_paragraph():
    """Blank lines become bare paragraphs (empty text nodes are invalid)."""
    doc = json.loads(markdown_to_prosemirror("a\n\nb"))
    assert doc["content"] == [
        {"type": "paragraph", "content": [{"type": "text", "text": "a"}]},
        {"type": "paragraph"},
        {"type": "paragraph", "content": [{"type": "text", "text": "b"}]},
    ]


def test_markdown_to_prosemirror_no_title():
    """Without a title there is no noteTitle node."""
    doc = json.loads(markdown_to_prosemirror("body only"))
    assert all(n["type"] != "noteTitle" for n in doc["content"])


def test_markdown_to_prosemirror_lists():
    """Bullet and ordered list lines become bulletList / orderedList nodes."""
    doc = json.loads(markdown_to_prosemirror("- one\n- two\n1. first\n2. second"))
    types = [n["type"] for n in doc["content"]]
    assert types == ["bulletList", "orderedList"]
    assert len(doc["content"][0]["content"]) == 2  # two bullet items
    assert doc["content"][0]["content"][0]["content"][0]["content"][0]["text"] == "one"
    assert doc["content"][1]["content"][1]["content"][0]["content"][0]["text"] == "second"


def test_markdown_prosemirror_roundtrip():
    """markdown_to_prosemirror output is readable back by prosemirror_to_markdown."""
    pm = markdown_to_prosemirror("First para\n\nSecond para", title="Round Trip")
    title, markdown = prosemirror_to_markdown(pm)
    assert title == "Round Trip"
    assert markdown == "First para\n\nSecond para"


def test_markdown_to_prosemirror_empty():
    """Empty content yields a valid empty doc."""
    doc = json.loads(markdown_to_prosemirror(""))
    assert doc["type"] == "doc"
    # No invalid empty text nodes anywhere.
    for node in doc["content"]:
        assert node.get("content") != [{"type": "text", "text": ""}]
