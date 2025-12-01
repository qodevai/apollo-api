"""Tests for Apollo utility functions."""

import json

from apollo.utils import normalize_linkedin_url, prosemirror_to_markdown


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
