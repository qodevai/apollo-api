"""Tests for Apollo client methods."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apollo.client import ApolloClient
from apollo.models import EmailerMessage, EmailTask, Task, TaskType


def _make_response(data: dict) -> MagicMock:
    """Create a mock httpx response with rate limit headers."""
    response = MagicMock()
    response.json.return_value = data
    response.headers = {
        "x-rate-limit-hourly": "400",
        "x-hourly-requests-left": "399",
        "x-rate-limit-minute": "200",
        "x-minute-requests-left": "199",
        "x-rate-limit-24-hour": "2000",
        "x-24-hour-requests-left": "1999",
    }
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def client() -> ApolloClient:
    """Create an ApolloClient with a mocked httpx client."""
    apollo = ApolloClient.__new__(ApolloClient)
    apollo._api_key = "test_key"
    apollo._rate_limit_status = {}
    apollo._client = AsyncMock()
    return apollo


# ============================================================================
# GET TASK
# ============================================================================


async def test_get_task(client: ApolloClient):
    """Test getting a task by ID."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {
            "task": {
                "id": "task_123",
                "type": "outreach_manual_email",
                "status": "scheduled",
                "emailer_message": {
                    "id": "em_456",
                    "subject": "Hello",
                    "status": "drafted",
                },
            }
        }
    )

    result = await client.get_task("task_123")

    assert isinstance(result, Task)
    assert result.id == "task_123"
    assert result.type == "outreach_manual_email"
    # emailer_message lives on EmailTask; base Task captures it via extra="allow"
    email_task = EmailTask.model_validate(result.model_dump())
    assert email_task.emailer_message is not None
    assert email_task.emailer_message.subject == "Hello"

    client._client.request.assert_called_once_with("GET", "/tasks/task_123")


# ============================================================================
# CREATE EMAIL TASK
# ============================================================================


async def test_create_email_task_basic(client: ApolloClient):
    """Test basic email task creation sets correct type."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {"task": {"id": "task_123", "type": "outreach_manual_email"}}
    )

    result = await client.create_email_task(
        contact_ids=["contact_1"],
        note="Follow up email",
    )

    assert isinstance(result, EmailTask)
    assert result.id == "task_123"
    assert result.type == "outreach_manual_email"

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/tasks")
    payload = call_args[1]["json"]
    assert payload["type"] == TaskType.OUTREACH_MANUAL_EMAIL
    assert payload["contact_ids"] == ["contact_1"]
    assert payload["note"] == "Follow up email"
    assert payload["priority"] == "medium"
    assert payload["status"] == "scheduled"


async def test_create_email_task_with_user_id(client: ApolloClient):
    """Test email task creation with assignee."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {"task": {"id": "task_123", "type": "outreach_manual_email"}}
    )

    await client.create_email_task(
        contact_ids=["contact_1"],
        note="Email",
        user_id="user_abc",
    )

    payload = client._client.request.call_args[1]["json"]
    assert payload["user_id"] == "user_abc"


async def test_create_email_task_with_due_at(client: ApolloClient):
    """Test email task creation with scheduling."""
    assert client._client is not None
    client._client.request.return_value = _make_response({"task": {"id": "task_123"}})

    await client.create_email_task(
        contact_ids=["contact_1"],
        note="Email",
        due_at=datetime(2026, 2, 19, 10, 0, 0, tzinfo=UTC),
    )

    payload = client._client.request.call_args[1]["json"]
    assert payload["due_at"] == "2026-02-19T10:00:00+00:00"


async def test_create_email_task_extra_fields(client: ApolloClient):
    """Test email task creation passes through extra fields."""
    assert client._client is not None
    client._client.request.return_value = _make_response({"task": {"id": "task_123"}})

    await client.create_email_task(
        contact_ids=["contact_1"],
        note="Email",
        custom_field="custom_value",
    )

    payload = client._client.request.call_args[1]["json"]
    assert payload["custom_field"] == "custom_value"


# ============================================================================
# UPDATE TASK
# ============================================================================


async def test_update_task_basic(client: ApolloClient):
    """Test basic task update."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {"task": {"id": "task_123", "priority": "high"}}
    )

    result = await client.update_task("task_123", priority="high")

    assert isinstance(result, Task)
    assert result.id == "task_123"

    call_args = client._client.request.call_args
    assert call_args[0] == ("PUT", "/tasks/task_123")
    payload = call_args[1]["json"]
    assert payload["priority"] == "high"


async def test_update_task_due_at(client: ApolloClient):
    """Test updating task due_at field."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {"task": {"id": "task_123", "due_at": "2026-02-19T10:00:00Z"}}
    )

    result = await client.update_task("task_123", due_at="2026-02-19T10:00:00Z")

    assert isinstance(result, Task)
    payload = client._client.request.call_args[1]["json"]
    assert payload["due_at"] == "2026-02-19T10:00:00Z"


# ============================================================================
# UPDATE EMAILER MESSAGE
# ============================================================================


async def test_update_emailer_message_subject_and_body(client: ApolloClient):
    """Test updating emailer message subject and body_html."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {
            "emailer_message": {
                "id": "em_456",
                "subject": "Test Subject",
                "body_text": "Hello world",
                "body_html": "<p>Hello world</p>",
                "status": "drafted",
            }
        }
    )

    result = await client.update_emailer_message(
        "em_456",
        subject="Test Subject",
        body_html="<p>Hello world</p>",
    )

    assert isinstance(result, EmailerMessage)
    assert result.subject == "Test Subject"

    call_args = client._client.request.call_args
    assert call_args[0] == ("PUT", "/emailer_messages/em_456")
    payload = call_args[1]["json"]
    assert payload["subject"] == "Test Subject"
    assert payload["body_html"] == "<p>Hello world</p>"


async def test_update_emailer_message_subject_only(client: ApolloClient):
    """Test updating only the subject."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {"emailer_message": {"id": "em_456", "subject": "New Subject"}}
    )

    await client.update_emailer_message("em_456", subject="New Subject")

    payload = client._client.request.call_args[1]["json"]
    assert payload["subject"] == "New Subject"
    assert "body_html" not in payload


async def test_update_emailer_message_extra_fields(client: ApolloClient):
    """Test passing extra fields like cc_emails."""
    assert client._client is not None
    client._client.request.return_value = _make_response({"emailer_message": {"id": "em_456"}})

    await client.update_emailer_message(
        "em_456",
        subject="Test",
        cc_emails=["cc@example.com"],
    )

    payload = client._client.request.call_args[1]["json"]
    assert payload["cc_emails"] == ["cc@example.com"]


# ============================================================================
# SEND EMAIL TASK
# ============================================================================


async def test_send_email_task(client: ApolloClient):
    """Test sending an email task immediately."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {
            "emailer_message": {
                "id": "em_456",
                "status": "scheduled",
                "async_sending": True,
                "due_at_source": "Email was sent using Send Now action",
            },
            "task": {"id": "task_123", "status": "completed"},
        }
    )

    result = await client.send_email_task("em_456")

    assert isinstance(result, EmailerMessage)
    assert result.status == "scheduled"

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/emailer_messages/em_456/send_now")
    payload = call_args[1]["json"]
    assert payload["surface"] == "tasks"
