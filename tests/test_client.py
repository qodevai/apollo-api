"""Tests for Apollo client methods."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from qodev_apollo_api.client import ApolloClient
from qodev_apollo_api.exceptions import APIError, AuthenticationError, RateLimitError
from qodev_apollo_api.models import (
    Account,
    AccountDetail,
    BaseTask,
    CalendarEvent,
    Call,
    Contact,
    ContactActionItemTask,
    ContactDetail,
    Conversation,
    ConversationDetail,
    Deal,
    Email,
    EmailerMessage,
    EmailTask,
    LinkedInConnectTask,
    LinkedInMessageTask,
    Note,
    OpportunityContactRoleType,
    PaginatedResponse,
    Pipeline,
    SortOrder,
    Stage,
    TaskType,
)


def _make_response(data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx response with rate limit headers."""
    response = MagicMock()
    response.json.return_value = data
    response.status_code = status_code
    response.text = "error"
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


def _make_error_response(status_code: int, retry_after: str | None = None) -> MagicMock:
    """Create a mock httpx response that raises HTTPStatusError."""
    response = MagicMock()
    response.status_code = status_code
    response.text = f"HTTP {status_code} error"
    response.headers = {"Retry-After": retry_after} if retry_after else {}
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
# INITIALIZATION & CONTEXT MANAGER
# ============================================================================


def test_init_with_api_key():
    """Test ApolloClient("key") sets _api_key."""
    c = ApolloClient("my_key")
    assert c._api_key == "my_key"
    assert c._client is None
    assert c._rate_limit_status == {}


def test_init_from_env():
    """Test reads APOLLO_API_KEY env var."""
    with patch.dict(os.environ, {"APOLLO_API_KEY": "env_key"}):
        c = ApolloClient()
        assert c._api_key == "env_key"


def test_init_missing_key_raises():
    """Test raises AuthenticationError when no key provided."""
    with patch.dict(os.environ, {}, clear=True):
        # Ensure APOLLO_API_KEY is not set
        os.environ.pop("APOLLO_API_KEY", None)
        with pytest.raises(AuthenticationError, match="No API key"):
            ApolloClient()


async def test_aenter_creates_httpx_client():
    """Test __aenter__ sets self._client."""
    c = ApolloClient("key")
    assert c._client is None
    async with c:
        assert c._client is not None
        assert isinstance(c._client, httpx.AsyncClient)


async def test_aexit_closes_client():
    """Test __aexit__ sets self._client = None."""
    c = ApolloClient("key")
    async with c:
        assert c._client is not None
    assert c._client is None


def test_rate_limit_status_property(client: ApolloClient):
    """Test returns _rate_limit_status dict."""
    client._rate_limit_status = {"hourly_limit": 400, "hourly_left": 399}
    assert client.rate_limit_status == {"hourly_limit": 400, "hourly_left": 399}


# ============================================================================
# ERROR HANDLING (_request)
# ============================================================================


async def test_request_without_context_manager_raises():
    """Test RuntimeError if _client is None."""
    c = ApolloClient.__new__(ApolloClient)
    c._api_key = "key"
    c._rate_limit_status = {}
    c._client = None
    with pytest.raises(RuntimeError, match="Client not initialized"):
        await c._request("GET", "/test")


async def test_request_401_raises_authentication_error(client: ApolloClient):
    """Test 401 raises AuthenticationError."""
    error_response = _make_error_response(401)
    client._client.request.return_value = _make_response({})
    client._client.request.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=error_response
    )
    with pytest.raises(AuthenticationError, match="Authentication failed"):
        await client._request("GET", "/test")


async def test_request_429_raises_rate_limit_error(client: ApolloClient):
    """Test 429 raises RateLimitError."""
    error_response = _make_error_response(429)
    client._client.request.return_value = _make_response({})
    client._client.request.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429", request=MagicMock(), response=error_response
    )
    with pytest.raises(RateLimitError, match="Rate limit exceeded"):
        await client._request("GET", "/test")


async def test_request_429_with_retry_after(client: ApolloClient):
    """Test 429 includes retry_after from header."""
    error_response = _make_error_response(429, retry_after="60")
    client._client.request.return_value = _make_response({})
    client._client.request.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429", request=MagicMock(), response=error_response
    )
    with pytest.raises(RateLimitError) as exc_info:
        await client._request("GET", "/test")
    assert exc_info.value.retry_after == 60


async def test_request_other_error_raises_api_error(client: ApolloClient):
    """Test other HTTP errors raise APIError."""
    error_response = _make_error_response(500)
    client._client.request.return_value = _make_response({})
    client._client.request.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=error_response
    )
    with pytest.raises(APIError) as exc_info:
        await client._request("GET", "/test")
    assert exc_info.value.status_code == 500


async def test_request_tracks_rate_limits(client: ApolloClient):
    """Test _rate_limit_status populated from headers."""
    client._client.request.return_value = _make_response({"ok": True})

    await client._request("GET", "/test")

    assert client._rate_limit_status == {
        "hourly_limit": 400,
        "hourly_left": 399,
        "minute_limit": 200,
        "minute_left": 199,
        "daily_limit": 2000,
        "daily_left": 1999,
    }


# ============================================================================
# SEARCH METHODS
# ============================================================================


async def test_search_contacts(client: ApolloClient):
    """Test POST /contacts/search returns PaginatedResponse[Contact]."""
    client._client.request.return_value = _make_response(
        {
            "contacts": [{"id": "c1", "first_name": "Alice"}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_contacts(q_keywords="Alice")

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], Contact)
    assert result.items[0].id == "c1"
    assert result.total == 1

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/contacts/search")
    payload = call_args[1]["json"]
    assert payload["q_keywords"] == "Alice"
    assert payload["page"] == 1
    assert payload["per_page"] == 100


async def test_search_accounts(client: ApolloClient):
    """Test POST /accounts/search returns PaginatedResponse[Account]."""
    client._client.request.return_value = _make_response(
        {
            "accounts": [{"id": "a1", "name": "Acme Corp"}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_accounts(q_organization_name="Acme")

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], Account)
    assert result.items[0].name == "Acme Corp"


async def test_search_deals(client: ApolloClient):
    """Test POST /opportunities/search returns PaginatedResponse[Deal]."""
    client._client.request.return_value = _make_response(
        {
            "opportunities": [{"id": "d1", "name": "Big Deal"}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_deals()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], Deal)
    assert result.items[0].name == "Big Deal"

    assert client._client.request.call_args[0] == ("POST", "/opportunities/search")


async def test_search_calls(client: ApolloClient):
    """Test POST /phone_calls/search returns PaginatedResponse[Call]."""
    client._client.request.return_value = _make_response(
        {
            "phone_calls": [{"id": "call1", "status": "completed"}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_calls()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], Call)

    assert client._client.request.call_args[0] == ("POST", "/phone_calls/search")


async def test_search_tasks(client: ApolloClient):
    """Test POST /tasks/search returns PaginatedResponse[Task]."""
    client._client.request.return_value = _make_response(
        {
            "tasks": [{"id": "t1", "type": "call"}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_tasks()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], BaseTask)

    assert client._client.request.call_args[0] == ("POST", "/tasks/search")


async def test_search_tasks_with_sort(client: ApolloClient):
    """Test search_tasks with sort parameter generates multi_sort payload."""
    client._client.request.return_value = _make_response(
        {"tasks": [], "pagination": {"total_entries": 0}}
    )

    await client.search_tasks(
        sort=[("task_priority", SortOrder.ASC), ("task_due_at", SortOrder.DESC)]
    )

    payload = client._client.request.call_args[1]["json"]
    assert payload["multi_sort"] == [
        {"task_priority": {"order": "asc"}},
        {"task_due_at": {"order": "desc"}},
    ]


async def test_search_tasks_with_filters(client: ApolloClient):
    """Test search_tasks with task_type_cds and user_ids."""
    client._client.request.return_value = _make_response(
        {"tasks": [], "pagination": {"total_entries": 0}}
    )

    await client.search_tasks(
        task_type_cds=[TaskType.CALL, TaskType.CONTACT_ACTION_ITEM],
        user_ids=["u1", "u2"],
    )

    payload = client._client.request.call_args[1]["json"]
    assert payload["task_type_cds"] == ["call", "contact_action_item"]
    assert payload["user_ids"] == ["u1", "u2"]


async def test_search_emails(client: ApolloClient):
    """Test POST /emailer_messages/search returns PaginatedResponse[Email]."""
    client._client.request.return_value = _make_response(
        {
            "emailer_messages": [{"id": "e1", "subject": "Hello"}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_emails()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], Email)

    assert client._client.request.call_args[0] == ("POST", "/emailer_messages/search")


async def test_search_notes(client: ApolloClient):
    """Test POST /notes/search with ProseMirror conversion."""
    prosemirror_json = (
        '{"type":"doc","content":'
        '[{"type":"noteTitle","content":[{"type":"text","text":"My Title"}]},'
        '{"type":"paragraph","content":[{"type":"text","text":"Hello world"}]}]}'
    )
    client._client.request.return_value = _make_response(
        {
            "notes": [{"id": "n1", "content": prosemirror_json}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_notes()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], Note)
    assert result.items[0].title == "My Title"
    assert result.items[0].content == "Hello world"

    assert client._client.request.call_args[0] == ("POST", "/notes/search")


async def test_search_calendar_events(client: ApolloClient):
    """Test POST /calendar_events/search returns PaginatedResponse[CalendarEvent]."""
    client._client.request.return_value = _make_response(
        {
            "calendar_events": [{"id": "ce1", "title": "Meeting"}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_calendar_events()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], CalendarEvent)

    assert client._client.request.call_args[0] == ("POST", "/calendar_events/search")


async def test_search_conversations(client: ApolloClient):
    """Test POST /conversations/search returns PaginatedResponse[Conversation]."""
    client._client.request.return_value = _make_response(
        {
            "conversations": [{"id": "cv1", "topic": "Sales call"}],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.search_conversations()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], Conversation)

    assert client._client.request.call_args[0] == ("POST", "/conversations/search")


# ============================================================================
# GET-BY-ID METHODS
# ============================================================================


async def test_get_contact(client: ApolloClient):
    """Test GET /contacts/{id} returns ContactDetail."""
    client._client.request.return_value = _make_response(
        {"contact": {"id": "c1", "first_name": "Alice", "employment_history": []}}
    )

    result = await client.get_contact("c1")

    assert isinstance(result, ContactDetail)
    assert result.id == "c1"
    assert result.first_name == "Alice"
    client._client.request.assert_called_once_with("GET", "/contacts/c1")


async def test_get_account(client: ApolloClient):
    """Test GET /accounts/{id} returns AccountDetail."""
    client._client.request.return_value = _make_response(
        {"account": {"id": "a1", "name": "Acme Corp"}}
    )

    result = await client.get_account("a1")

    assert isinstance(result, AccountDetail)
    assert result.id == "a1"
    assert result.name == "Acme Corp"
    client._client.request.assert_called_once_with("GET", "/accounts/a1")


async def test_get_deal(client: ApolloClient):
    """Test GET /opportunities/{id} returns Deal."""
    client._client.request.return_value = _make_response(
        {"opportunity": {"id": "d1", "name": "Big Deal"}}
    )

    result = await client.get_deal("d1")

    assert isinstance(result, Deal)
    assert result.id == "d1"
    client._client.request.assert_called_once_with("GET", "/opportunities/d1")


async def test_get_pipeline(client: ApolloClient):
    """Test GET /opportunity_pipelines/{id} returns Pipeline."""
    client._client.request.return_value = _make_response(
        {"opportunity_pipeline": {"id": "p1", "title": "Sales"}}
    )

    result = await client.get_pipeline("p1")

    assert isinstance(result, Pipeline)
    assert result.id == "p1"
    assert result.title == "Sales"
    client._client.request.assert_called_once_with("GET", "/opportunity_pipelines/p1")


async def test_get_conversation(client: ApolloClient):
    """Test GET /conversations/{id} returns ConversationDetail (no wrapping key)."""
    client._client.request.return_value = _make_response(
        {"id": "cv1", "topic": "Demo", "transcript": []}
    )

    result = await client.get_conversation("cv1")

    assert isinstance(result, ConversationDetail)
    assert result.id == "cv1"
    assert result.topic == "Demo"
    client._client.request.assert_called_once_with("GET", "/conversations/cv1")


# ============================================================================
# LIST METHODS
# ============================================================================


async def test_list_pipelines(client: ApolloClient):
    """Test GET /opportunity_pipelines returns PaginatedResponse[Pipeline]."""
    client._client.request.return_value = _make_response(
        {"opportunity_pipelines": [{"id": "p1"}, {"id": "p2"}]}
    )

    result = await client.list_pipelines()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 2
    assert all(isinstance(p, Pipeline) for p in result.items)
    client._client.request.assert_called_once_with("GET", "/opportunity_pipelines")


async def test_list_pipeline_stages(client: ApolloClient):
    """Test GET /opportunity_stages filtered by pipeline_id."""
    client._client.request.return_value = _make_response(
        {
            "opportunity_stages": [
                {"id": "s1", "opportunity_pipeline_id": "p1"},
                {"id": "s2", "opportunity_pipeline_id": "p2"},
                {"id": "s3", "opportunity_pipeline_id": "p1"},
            ]
        }
    )

    result = await client.list_pipeline_stages("p1")

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 2
    assert all(isinstance(s, Stage) for s in result.items)
    assert {s.id for s in result.items} == {"s1", "s3"}


async def test_list_all_stages(client: ApolloClient):
    """Test GET /opportunity_stages returns all stages unfiltered."""
    client._client.request.return_value = _make_response(
        {
            "opportunity_stages": [
                {"id": "s1", "opportunity_pipeline_id": "p1"},
                {"id": "s2", "opportunity_pipeline_id": "p2"},
            ]
        }
    )

    result = await client.list_all_stages()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 2


async def test_list_opportunity_contact_role_types(client: ApolloClient):
    """Test POST /opportunity_contact_role_types/search returns role types."""
    client._client.request.return_value = _make_response(
        {
            "opportunity_contact_role_types": [
                {"id": "rt1", "name": "Decision Maker", "display_order": 3.0},
                {"id": "rt2", "name": "Buyer", "display_order": 1.0},
            ]
        }
    )

    result = await client.list_opportunity_contact_role_types()

    assert isinstance(result, PaginatedResponse)
    assert len(result.items) == 2
    assert all(isinstance(rt, OpportunityContactRoleType) for rt in result.items)
    assert result.items[0].name == "Decision Maker"
    assert result.items[1].name == "Buyer"
    assert result.total == 2

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/opportunity_contact_role_types/search")
    assert call_args[1]["json"] == {}


async def test_get_contact_stages(client: ApolloClient):
    """Test GET /contact_stages returns list[dict]."""
    client._client.request.return_value = _make_response(
        {"contact_stages": [{"id": "cs1", "name": "Lead"}, {"id": "cs2", "name": "Customer"}]}
    )

    result = await client.get_contact_stages()

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "Lead"
    client._client.request.assert_called_once_with("GET", "/contact_stages")


async def test_list_contact_calls(client: ApolloClient):
    """Test GET /contacts/{id}/calls returns list[Call]."""
    client._client.request.return_value = _make_response(
        {"calls": [{"id": "call1"}, {"id": "call2"}]}
    )

    result = await client.list_contact_calls("c1")

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(c, Call) for c in result)
    client._client.request.assert_called_once_with("GET", "/contacts/c1/calls")


async def test_list_contact_tasks(client: ApolloClient):
    """Test GET /contacts/{id}/tasks returns list[Task]."""
    client._client.request.return_value = _make_response(
        {"tasks": [{"id": "t1", "type": "call"}, {"id": "t2", "type": "contact_action_item"}]}
    )

    result = await client.list_contact_tasks("c1")

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(t, BaseTask) for t in result)
    client._client.request.assert_called_once_with("GET", "/contacts/c1/tasks")


async def test_list_account_news(client: ApolloClient):
    """Test GET /accounts/{id}/news returns list[dict]."""
    client._client.request.return_value = _make_response(
        {"news": [{"title": "Big news"}, {"title": "Small news"}]}
    )

    result = await client.list_account_news("a1")

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "Big news"
    client._client.request.assert_called_once_with("GET", "/accounts/a1/news")


async def test_list_account_jobs(client: ApolloClient):
    """Test GET /accounts/{id}/job_postings returns list[dict]."""
    client._client.request.return_value = _make_response(
        {"job_postings": [{"title": "Engineer"}, {"title": "Designer"}]}
    )

    result = await client.list_account_jobs("a1")

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "Engineer"
    client._client.request.assert_called_once_with("GET", "/accounts/a1/job_postings")


# ============================================================================
# CREATE / MUTATE METHODS
# ============================================================================


async def test_create_contact(client: ApolloClient):
    """Test POST /contacts returns Contact."""
    client._client.request.return_value = _make_response(
        {"contact": {"id": "c_new", "first_name": "Bob", "last_name": "Smith"}}
    )

    result = await client.create_contact("Bob", "Smith", email="bob@example.com")

    assert isinstance(result, Contact)
    assert result.id == "c_new"

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/contacts")
    payload = call_args[1]["json"]
    assert payload["first_name"] == "Bob"
    assert payload["last_name"] == "Smith"
    assert payload["email"] == "bob@example.com"


async def test_update_contact(client: ApolloClient):
    """Test PUT /contacts/{id} returns Contact."""
    client._client.request.return_value = _make_response({"contact": {"id": "c1", "title": "CTO"}})

    result = await client.update_contact("c1", title="CTO")

    assert isinstance(result, Contact)
    assert result.id == "c1"

    call_args = client._client.request.call_args
    assert call_args[0] == ("PUT", "/contacts/c1")
    payload = call_args[1]["json"]
    assert payload["title"] == "CTO"


async def test_create_task(client: ApolloClient):
    """Test POST /tasks returns specific Task subclass."""
    client._client.request.return_value = _make_response(
        {"task": {"id": "t_new", "type": "contact_action_item"}}
    )

    result = await client.create_task(contact_ids=["c1"], note="Follow up", priority="high")

    assert isinstance(result, ContactActionItemTask)
    assert result.id == "t_new"

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/tasks")
    payload = call_args[1]["json"]
    assert payload["contact_ids"] == ["c1"]
    assert payload["note"] == "Follow up"
    assert payload["priority"] == "high"


async def test_create_task_empty_contact_ids_raises(client: ApolloClient):
    """Test ValueError when contact_ids is empty."""
    with pytest.raises(ValueError, match="contact_ids must not be empty"):
        await client.create_task(contact_ids=[], note="Test")


async def test_complete_task(client: ApolloClient):
    """Test POST /tasks/{id}/complete."""
    client._client.request.return_value = _make_response(
        {"task": {"id": "t1", "type": "call", "status": "complete"}}
    )

    result = await client.complete_task("t1")

    assert isinstance(result, BaseTask)
    assert result.status == "complete"

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/tasks/t1/complete")
    payload = call_args[1]["json"]
    assert "note" not in payload


async def test_complete_task_with_note(client: ApolloClient):
    """Test complete_task passes note in payload."""
    client._client.request.return_value = _make_response(
        {"task": {"id": "t1", "type": "call", "status": "complete"}}
    )

    await client.complete_task("t1", note="Done via API")

    payload = client._client.request.call_args[1]["json"]
    assert payload["note"] == "Done via API"


async def test_create_linkedin_connect_task(client: ApolloClient):
    """Test linkedin connect task sets standalone_outreach_task_message."""
    client._client.request.return_value = _make_response(
        {"task": {"id": "t1", "type": "linkedin_step_connect"}}
    )

    result = await client.create_linkedin_connect_task(
        contact_id="c1",
        title="Connect John",
        message="Let's connect!",
    )

    assert isinstance(result, LinkedInConnectTask)

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/tasks")
    payload = call_args[1]["json"]
    assert payload["type"] == TaskType.LINKEDIN_STEP_CONNECT
    assert payload["contact_ids"] == ["c1"]
    assert payload["standalone_outreach_task_message"] == {
        "body_text": "Let's connect!",
        "subject": "",
    }


async def test_create_linkedin_message_task(client: ApolloClient):
    """Test linkedin message task sets standalone_outreach_task_message."""
    client._client.request.return_value = _make_response(
        {"task": {"id": "t1", "type": "linkedin_step_message"}}
    )

    result = await client.create_linkedin_message_task(
        contact_id="c1",
        title="Message John",
        message="Hello John!",
    )

    assert isinstance(result, LinkedInMessageTask)

    payload = client._client.request.call_args[1]["json"]
    assert payload["type"] == TaskType.LINKEDIN_STEP_MESSAGE
    assert payload["standalone_outreach_task_message"] == {
        "body_text": "Hello John!",
        "subject": "",
    }


async def test_skip_tasks(client: ApolloClient):
    """Test POST /tasks/bulk_skip."""
    client._client.request.return_value = _make_response({"success": True})

    result = await client.skip_tasks(["t1", "t2"])

    assert result == {"success": True}

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/tasks/bulk_skip")
    payload = call_args[1]["json"]
    assert payload["ids"] == ["t1", "t2"]
    assert payload["on_task_page"] is True


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

    assert isinstance(result, EmailTask)
    assert result.id == "task_123"
    assert result.type == "outreach_manual_email"
    assert result.emailer_message is not None
    assert result.emailer_message.subject == "Hello"

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
        {"task": {"id": "task_123", "type": "contact_action_item", "priority": "high"}}
    )

    result = await client.update_task("task_123", priority="high")

    assert isinstance(result, BaseTask)
    assert result.id == "task_123"

    call_args = client._client.request.call_args
    assert call_args[0] == ("PUT", "/tasks/task_123")
    payload = call_args[1]["json"]
    assert payload["priority"] == "high"


async def test_update_task_due_at(client: ApolloClient):
    """Test updating task due_at field."""
    assert client._client is not None
    client._client.request.return_value = _make_response(
        {"task": {"id": "task_123", "type": "call", "due_at": "2026-02-19T10:00:00Z"}}
    )

    result = await client.update_task("task_123", due_at="2026-02-19T10:00:00Z")

    assert isinstance(result, BaseTask)
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


# ============================================================================
# ENRICHMENT & USAGE
# ============================================================================


async def test_enrich_organization(client: ApolloClient):
    """Test POST /organizations/enrich."""
    client._client.request.return_value = _make_response(
        {"organization": {"name": "Apollo", "domain": "apollo.io"}}
    )

    result = await client.enrich_organization("apollo.io")

    assert result == {"name": "Apollo", "domain": "apollo.io"}

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/organizations/enrich")
    payload = call_args[1]["json"]
    assert payload["domain"] == "apollo.io"


async def test_enrich_person(client: ApolloClient):
    """Test POST /people/match."""
    client._client.request.return_value = _make_response(
        {"person": {"first_name": "Alice", "email": "alice@example.com"}}
    )

    result = await client.enrich_person("alice@example.com")

    assert result == {"first_name": "Alice", "email": "alice@example.com"}

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/people/match")
    payload = call_args[1]["json"]
    assert payload["email"] == "alice@example.com"


async def test_search_people(client: ApolloClient):
    """Test POST /mixed_people/search."""
    client._client.request.return_value = _make_response(
        {"people": [{"id": "p1", "name": "Alice"}]}
    )

    result = await client.search_people(q_keywords="Alice")

    assert result == {"people": [{"id": "p1", "name": "Alice"}]}

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/mixed_people/search")
    payload = call_args[1]["json"]
    assert payload["q_keywords"] == "Alice"


async def test_create_note(client: ApolloClient):
    """Test POST /notes."""
    client._client.request.return_value = _make_response({"note": {"id": "n1", "content": "Hello"}})

    result = await client.create_note("Hello")

    assert result == {"note": {"id": "n1", "content": "Hello"}}

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/notes")
    payload = call_args[1]["json"]
    assert payload["note"] == "Hello"
    assert "contact_ids" not in payload


async def test_create_note_with_associations(client: ApolloClient):
    """Test create_note with contact_ids, account_ids, opportunity_ids."""
    client._client.request.return_value = _make_response({"note": {"id": "n1"}})

    await client.create_note(
        "Meeting notes",
        contact_ids=["c1", "c2"],
        account_ids=["a1"],
        opportunity_ids=["o1"],
    )

    payload = client._client.request.call_args[1]["json"]
    assert payload["note"] == "Meeting notes"
    assert payload["contact_ids"] == ["c1", "c2"]
    assert payload["account_ids"] == ["a1"]
    assert payload["opportunity_ids"] == ["o1"]


async def test_get_api_usage(client: ApolloClient):
    """Test POST /usage_stats/api_usage_stats."""
    usage_data = {
        '["api/v1/contacts", "search"]': {
            "day_limit": 1000,
            "day_consumed": 42,
        }
    }
    client._client.request.return_value = _make_response(usage_data)

    result = await client.get_api_usage()

    assert '["api/v1/contacts", "search"]' in result

    call_args = client._client.request.call_args
    assert call_args[0] == ("POST", "/usage_stats/api_usage_stats")


# ============================================================================
# FIND CONTACT BY LINKEDIN URL (3-tier strategy)
# ============================================================================


async def test_find_by_linkedin_url_step1_match(client: ApolloClient):
    """Test URL search returns exact match."""
    client._client.request.return_value = _make_response(
        {
            "contacts": [
                {"id": "c1", "linkedin_url": "https://www.linkedin.com/in/alice"},
            ],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.find_contact_by_linkedin_url("https://www.linkedin.com/in/alice")

    assert result == "c1"


async def test_find_by_linkedin_url_step1_no_url_match(client: ApolloClient):
    """Test URL search returns contacts but none match the URL."""
    # Step 1: URL search returns contact with different linkedin_url
    # Step 2: No person_name provided, so no name search
    client._client.request.return_value = _make_response(
        {
            "contacts": [
                {"id": "c1", "linkedin_url": "https://www.linkedin.com/in/bob"},
            ],
            "pagination": {"total_entries": 1},
        }
    )

    result = await client.find_contact_by_linkedin_url("https://www.linkedin.com/in/alice")

    assert result is None


async def test_find_by_linkedin_url_step2_name_fallback(client: ApolloClient):
    """Test name search finds unique match when URL search fails."""
    # Step 1: URL search returns no contacts
    step1_response = _make_response({"contacts": [], "pagination": {"total_entries": 0}})
    # Step 2: Name search returns one matching contact
    step2_response = _make_response(
        {
            "contacts": [
                {"id": "c1", "linkedin_url": "https://www.linkedin.com/in/alice"},
            ],
            "pagination": {"total_entries": 1},
        }
    )
    client._client.request.side_effect = [step1_response, step2_response]

    result = await client.find_contact_by_linkedin_url(
        "https://www.linkedin.com/in/alice",
        person_name="Alice Smith",
    )

    assert result == "c1"


async def test_find_by_linkedin_url_step2_ambiguous(client: ApolloClient):
    """Test name search finds multiple → returns None."""
    step1_response = _make_response({"contacts": [], "pagination": {"total_entries": 0}})
    step2_response = _make_response(
        {
            "contacts": [
                {"id": "c1", "linkedin_url": "https://www.linkedin.com/in/alice"},
                {"id": "c2", "linkedin_url": "https://www.linkedin.com/in/alice"},
            ],
            "pagination": {"total_entries": 2},
        }
    )
    client._client.request.side_effect = [step1_response, step2_response]

    result = await client.find_contact_by_linkedin_url(
        "https://www.linkedin.com/in/alice",
        person_name="Alice Smith",
    )

    assert result is None


async def test_find_by_linkedin_url_step3_create(client: ApolloClient):
    """Test people DB match → creates contact."""
    step1_response = _make_response({"contacts": [], "pagination": {"total_entries": 0}})
    # Step 2: Name search — no URL match
    step2_response = _make_response({"contacts": [], "pagination": {"total_entries": 0}})
    # Step 3: People DB search
    step3_response = _make_response(
        {
            "people": [
                {
                    "id": "person_1",
                    "first_name": "Alice",
                    "last_name": "Smith",
                    "linkedin_url": "https://www.linkedin.com/in/alice",
                    "title": "CTO",
                }
            ]
        }
    )
    # Step 3: Create contact
    step4_response = _make_response(
        {"contact": {"id": "c_new", "first_name": "Alice", "last_name": "Smith"}}
    )
    client._client.request.side_effect = [
        step1_response,
        step2_response,
        step3_response,
        step4_response,
    ]

    result = await client.find_contact_by_linkedin_url(
        "https://www.linkedin.com/in/alice",
        person_name="Alice Smith",
        create_if_missing=True,
        contact_stage_id="stage_1",
    )

    assert result == "c_new"

    # Verify create_contact was called with correct data
    create_call = client._client.request.call_args_list[3]
    assert create_call[0] == ("POST", "/contacts")
    payload = create_call[1]["json"]
    assert payload["first_name"] == "Alice"
    assert payload["last_name"] == "Smith"
    assert payload["person_id"] == "person_1"
    assert payload["contact_stage_id"] == "stage_1"


async def test_find_by_linkedin_url_not_found(client: ApolloClient):
    """Test all three steps fail → None."""
    step1_response = _make_response({"contacts": [], "pagination": {"total_entries": 0}})
    step2_response = _make_response({"contacts": [], "pagination": {"total_entries": 0}})
    # Step 3: People DB — no URL match
    step3_response = _make_response(
        {
            "people": [
                {
                    "id": "person_1",
                    "first_name": "Bob",
                    "last_name": "Jones",
                    "linkedin_url": "https://www.linkedin.com/in/bob",
                }
            ]
        }
    )
    client._client.request.side_effect = [
        step1_response,
        step2_response,
        step3_response,
    ]

    result = await client.find_contact_by_linkedin_url(
        "https://www.linkedin.com/in/alice",
        person_name="Alice Smith",
        create_if_missing=True,
    )

    assert result is None
