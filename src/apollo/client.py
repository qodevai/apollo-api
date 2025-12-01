"""Apollo API Client.

Type-safe async wrapper for Apollo.io API.
"""

import os
from types import TracebackType

import httpx

from .exceptions import APIError, AuthenticationError, RateLimitError
from .models import (
    Account,
    Call,
    Contact,
    Deal,
    Email,
    Note,
    PaginatedResponse,
    Pipeline,
    Stage,
    Task,
)
from .utils import normalize_linkedin_url, prosemirror_to_markdown


class ApolloClient:
    """Async Apollo.io API client with context manager support."""

    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        """Initialize client with API key.

        Args:
            api_key: Apollo API key. Falls back to APOLLO_API_KEY environment variable.
            timeout: Request timeout in seconds (default: 30)

        Raises:
            AuthenticationError: If no API key provided
        """
        self._api_key = api_key or os.getenv("APOLLO_API_KEY")
        if not self._api_key:
            raise AuthenticationError(
                "No API key provided. Pass api_key parameter or set APOLLO_API_KEY environment variable."
            )

        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._rate_limit_status: dict[str, int] = {}

    async def __aenter__(self) -> "ApolloClient":
        """Enter async context manager."""
        # _api_key is guaranteed to be str here (checked in __init__)
        assert self._api_key is not None
        self._client = httpx.AsyncClient(
            base_url="https://api.apollo.io/api/v1",
            headers={
                "x-api-key": self._api_key,
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "accept": "application/json",
            },
            timeout=self._timeout,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager and close client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def rate_limit_status(self) -> dict[str, int]:
        """Current rate limit status from last request.

        Returns:
            Dictionary with keys: hourly_limit, hourly_left, minute_limit, minute_left, daily_limit, daily_left
        """
        return self._rate_limit_status

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make HTTP request with error handling and rate limit tracking.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            Response JSON data

        Raises:
            AuthenticationError: On 401
            RateLimitError: On 429
            APIError: On other errors
        """
        if not self._client:
            raise RuntimeError(
                "Client not initialized. Use 'async with ApolloClient()' context manager."
            )

        try:
            response = await self._client.request(method, endpoint, **kwargs)

            # Track rate limits from headers
            headers = response.headers
            self._rate_limit_status = {
                "hourly_limit": int(headers.get("x-rate-limit-hourly", 0)),
                "hourly_left": int(headers.get("x-hourly-requests-left", 0)),
                "minute_limit": int(headers.get("x-rate-limit-minute", 0)),
                "minute_left": int(headers.get("x-minute-requests-left", 0)),
                "daily_limit": int(headers.get("x-rate-limit-24-hour", 0)),
                "daily_left": int(headers.get("x-24-hour-requests-left", 0)),
            }

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed. Check your API key.") from e
            elif e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                raise RateLimitError(
                    "Rate limit exceeded. Apollo limits: 400/hour, 200/min, 2000/day",
                    retry_after=int(retry_after) if retry_after else None,
                ) from e
            else:
                raise APIError(
                    f"API request failed: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e

    async def _post(self, endpoint: str, data: dict) -> dict:
        """Make POST request."""
        return await self._request("POST", endpoint, json=data)

    async def _get(self, endpoint: str) -> dict:
        """Make GET request."""
        return await self._request("GET", endpoint)

    # ========================================================================
    # CONTACTS
    # ========================================================================

    async def search_contacts(
        self, page: int = 1, limit: int = 100, **filters
    ) -> PaginatedResponse[Contact]:
        """Search contacts with filters.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            **filters: Additional filters (q_keywords, contact_stage_ids, linkedin_url, etc.)

        Returns:
            Paginated response with Contact items
        """
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/contacts/search", data)

        contacts = [Contact.model_validate(c) for c in result.get("contacts", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Contact](
            items=contacts,
            total=pagination.get("total_entries", len(contacts)),
            page=page,
        )

    async def get_contact(self, contact_id: str) -> Contact:
        """Get contact details by ID.

        Args:
            contact_id: Contact ID

        Returns:
            Contact model
        """
        result = await self._get(f"/contacts/{contact_id}")
        return Contact.model_validate(result.get("contact", {}))

    async def create_contact(
        self,
        first_name: str,
        last_name: str,
        **fields,
    ) -> dict:
        """Create a new contact.

        Args:
            first_name: Contact first name
            last_name: Contact last name
            **fields: Additional fields (email, title, company_name, linkedin_url, etc.)

        Returns:
            Raw API response with created contact data
        """
        data = {
            "first_name": first_name,
            "last_name": last_name,
            **fields,
        }
        return await self._post("/contacts", data)

    async def get_contact_stages(self) -> list[dict]:
        """Get all contact stages.

        Returns:
            List of contact stage dictionaries
        """
        result = await self._get("/contact_stages")
        return result.get("contact_stages", [])

    async def find_contact_by_linkedin_url(
        self,
        linkedin_url: str,
        person_name: str | None = None,
        create_if_missing: bool = False,
        contact_stage_id: str | None = None,
    ) -> str | None:
        """Find contact using 3-tier fallback strategy.

        Strategy:
        1. Search by LinkedIn URL (exact match)
        2. Fallback to name search (if unique match)
        3. People database search for auto-creation (if enabled)

        Args:
            linkedin_url: LinkedIn profile URL
            person_name: Person's full name (for fallback search)
            create_if_missing: Auto-create from people database if not found
            contact_stage_id: Stage ID to assign when creating

        Returns:
            Contact ID if found/created, None otherwise
        """
        normalized_url = normalize_linkedin_url(linkedin_url)

        # Step 1: Search by LinkedIn URL
        result = await self.search_contacts(linkedin_url=normalized_url, limit=5)
        if result.items:
            # Verify URL matches (LinkedIn URLs can change)
            for contact in result.items:
                if (
                    contact.linkedin_url
                    and normalize_linkedin_url(contact.linkedin_url) == normalized_url
                ):
                    return contact.id

        # Step 2: Fallback to name search
        if person_name:
            result = await self.search_contacts(q_keywords=person_name, limit=10)
            matches = [
                c
                for c in result.items
                if c.linkedin_url and normalize_linkedin_url(c.linkedin_url) == normalized_url
            ]
            if len(matches) == 1:
                return matches[0].id
            elif len(matches) > 1:
                # Ambiguous - multiple contacts with same name and URL
                return None

        # Step 3: People database search for auto-creation
        if create_if_missing and person_name:
            people_result = await self._post(
                "/mixed_people/search",
                {
                    "q_keywords": person_name,
                    "per_page": 10,
                },
            )

            people = people_result.get("people", [])
            for person in people:
                person_url = person.get("linkedin_url", "")
                if person_url and normalize_linkedin_url(person_url) == normalized_url:
                    # Create contact from people database
                    create_data = {
                        "first_name": person.get("first_name", ""),
                        "last_name": person.get("last_name", ""),
                        "linkedin_url": person.get("linkedin_url"),
                        "title": person.get("title"),
                        "person_id": person.get("id"),
                    }
                    if contact_stage_id:
                        create_data["contact_stage_id"] = contact_stage_id

                    created = await self.create_contact(**create_data)
                    return created.get("contact", {}).get("id")

        return None

    # ========================================================================
    # ACCOUNTS
    # ========================================================================

    async def search_accounts(
        self, page: int = 1, limit: int = 100, **filters
    ) -> PaginatedResponse[Account]:
        """Search accounts with filters.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            **filters: Additional filters (q_organization_name, account_stage_ids, etc.)

        Returns:
            Paginated response with Account items
        """
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/accounts/search", data)

        accounts = [Account.model_validate(a) for a in result.get("accounts", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Account](
            items=accounts,
            total=pagination.get("total_entries", len(accounts)),
            page=page,
        )

    async def get_account(self, account_id: str) -> Account:
        """Get account details by ID.

        Args:
            account_id: Account ID

        Returns:
            Account model
        """
        result = await self._get(f"/accounts/{account_id}")
        return Account.model_validate(result.get("account", {}))

    # ========================================================================
    # DEALS / OPPORTUNITIES
    # ========================================================================

    async def search_deals(
        self, page: int = 1, limit: int = 100, **filters
    ) -> PaginatedResponse[Deal]:
        """Search deals/opportunities with filters.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            **filters: Additional filters (opportunity_stage_ids, q_keywords, etc.)

        Returns:
            Paginated response with Deal items
        """
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/opportunities/search", data)

        deals = [Deal.model_validate(d) for d in result.get("opportunities", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Deal](
            items=deals,
            total=pagination.get("total_entries", len(deals)),
            page=page,
        )

    async def get_deal(self, deal_id: str) -> Deal:
        """Get deal details by ID.

        Args:
            deal_id: Deal/Opportunity ID

        Returns:
            Deal model
        """
        result = await self._get(f"/opportunities/{deal_id}")
        return Deal.model_validate(result.get("opportunity", {}))

    # ========================================================================
    # PIPELINES & STAGES
    # ========================================================================

    async def list_pipelines(self, page: int = 1, limit: int = 100) -> PaginatedResponse[Pipeline]:
        """List all pipelines.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100)

        Returns:
            Paginated response with Pipeline items
        """
        result = await self._get("/opportunity_pipelines")
        pipelines = [Pipeline.model_validate(p) for p in result.get("opportunity_pipelines", [])]

        return PaginatedResponse[Pipeline](
            items=pipelines,
            total=len(pipelines),
            page=page,
        )

    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """Get pipeline details by ID.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Pipeline model
        """
        result = await self._get(f"/opportunity_pipelines/{pipeline_id}")
        return Pipeline.model_validate(result.get("opportunity_pipeline", {}))

    async def list_pipeline_stages(
        self, pipeline_id: str, page: int = 1, limit: int = 100
    ) -> PaginatedResponse[Stage]:
        """List stages for a pipeline.

        Args:
            pipeline_id: Pipeline ID
            page: Page number (default 1)
            limit: Results per page (default 100)

        Returns:
            Paginated response with Stage items
        """
        # Get all stages and filter by pipeline_id
        result = await self._get("/opportunity_stages")
        all_stages = result.get("opportunity_stages", [])

        # Filter by pipeline_id
        stages = [
            Stage.model_validate(s)
            for s in all_stages
            if s.get("opportunity_pipeline_id") == pipeline_id
        ]

        return PaginatedResponse[Stage](
            items=stages,
            total=len(stages),
            page=page,
        )

    # ========================================================================
    # ENRICHMENT
    # ========================================================================

    async def enrich_organization(self, domain: str) -> dict:
        """Enrich organization data by domain.

        Searches Apollo's database of 35M+ organizations.

        Args:
            domain: Company domain (e.g., "apollo.io")

        Returns:
            Organization data dictionary
        """
        result = await self._post("/organizations/enrich", {"domain": domain})
        return result.get("organization", {})

    async def enrich_person(self, email: str) -> dict:
        """Enrich person data by email.

        Searches Apollo's database of 210M+ people. Costs 1 enrichment credit.

        Args:
            email: Person's email address

        Returns:
            Person data dictionary
        """
        result = await self._post("/people/match", {"email": email})
        return result.get("person", {})

    async def search_people(self, **filters) -> dict:
        """Search people in Apollo's global database.

        Args:
            **filters: Search filters (q_keywords, person_titles, person_locations, etc.)

        Returns:
            Search results dictionary
        """
        return await self._post("/mixed_people/search", filters)

    # ========================================================================
    # NOTES
    # ========================================================================

    async def search_notes(
        self, page: int = 1, limit: int = 100, **filters
    ) -> PaginatedResponse[Note]:
        """Search notes with filters.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            **filters: Additional filters (contact_ids, account_ids, etc.)

        Returns:
            Paginated response with Note items (content converted to Markdown)
        """
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/notes/search", data)

        notes = []
        for note_data in result.get("notes", []):
            # Convert ProseMirror JSON to Markdown
            content_json = note_data.get("content", "{}")
            title, markdown = prosemirror_to_markdown(content_json)

            notes.append(
                Note(
                    id=note_data.get("id"),
                    title=title,
                    content=markdown,
                    created_at=note_data.get("created_at"),
                    updated_at=note_data.get("updated_at"),
                    user_id=note_data.get("user_id"),
                    contact_ids=note_data.get("contact_ids", []),
                    account_ids=note_data.get("account_ids", []),
                    opportunity_ids=note_data.get("opportunity_ids", []),
                    pinned_to_top=note_data.get("pinned_to_top", False),
                )
            )

        pagination = result.get("pagination", {})
        return PaginatedResponse[Note](
            items=notes,
            total=pagination.get("total_entries", len(notes)),
            page=page,
        )

    async def create_note(
        self,
        content: str,
        contact_ids: list[str] | None = None,
        account_ids: list[str] | None = None,
        opportunity_ids: list[str] | None = None,
    ) -> dict:
        """Create a note.

        Args:
            content: Note content (plain text or Markdown)
            contact_ids: List of contact IDs to associate
            account_ids: List of account IDs to associate
            opportunity_ids: List of opportunity IDs to associate

        Returns:
            Raw API response with created note data
        """
        data: dict[str, str | list[str]] = {"note": content}
        if contact_ids:
            data["contact_ids"] = contact_ids
        if account_ids:
            data["account_ids"] = account_ids
        if opportunity_ids:
            data["opportunity_ids"] = opportunity_ids

        return await self._post("/notes", data)

    # ========================================================================
    # ACTIVITIES
    # ========================================================================

    async def search_calls(
        self, page: int = 1, limit: int = 100, **filters
    ) -> PaginatedResponse[Call]:
        """Search call activities.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            **filters: Additional filters

        Returns:
            Paginated response with Call items
        """
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/phone_calls/search", data)

        calls = [Call.model_validate(c) for c in result.get("phone_calls", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Call](
            items=calls,
            total=pagination.get("total_entries", len(calls)),
            page=page,
        )

    async def search_tasks(
        self, page: int = 1, limit: int = 100, **filters
    ) -> PaginatedResponse[Task]:
        """Search task activities.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            **filters: Additional filters

        Returns:
            Paginated response with Task items
        """
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/tasks/search", data)

        tasks = [Task.model_validate(t) for t in result.get("tasks", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Task](
            items=tasks,
            total=pagination.get("total_entries", len(tasks)),
            page=page,
        )

    async def search_emails(
        self, page: int = 1, limit: int = 100, **filters
    ) -> PaginatedResponse[Email]:
        """Search email activities.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            **filters: Additional filters

        Returns:
            Paginated response with Email items
        """
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/emailer_messages/search", data)

        emails = [Email.model_validate(e) for e in result.get("emailer_messages", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Email](
            items=emails,
            total=pagination.get("total_entries", len(emails)),
            page=page,
        )

    async def create_task(
        self,
        contact_ids: list[str],
        note: str,
        type: str = "action_item",
        priority: str = "medium",
        **fields,
    ) -> dict:
        """Create a task.

        Args:
            contact_ids: List of contact IDs
            note: Task description
            type: Task type (action_item, call, etc.)
            priority: Task priority (high, medium, low)
            **fields: Additional fields (due_at, etc.)

        Returns:
            Raw API response with created task data
        """
        data = {
            "contact_ids": contact_ids,
            "note": note,
            "type": type,
            "priority": priority,
            **fields,
        }
        return await self._post("/tasks", data)

    async def list_contact_calls(self, contact_id: str) -> list[dict]:
        """List calls for a contact.

        Args:
            contact_id: Contact ID

        Returns:
            List of call dictionaries
        """
        result = await self._get(f"/contacts/{contact_id}/calls")
        return result.get("calls", [])

    async def list_contact_tasks(self, contact_id: str) -> list[dict]:
        """List tasks for a contact.

        Args:
            contact_id: Contact ID

        Returns:
            List of task dictionaries
        """
        result = await self._get(f"/contacts/{contact_id}/tasks")
        return result.get("tasks", [])

    # ========================================================================
    # NEWS & JOBS
    # ========================================================================

    async def list_account_news(self, account_id: str) -> list[dict]:
        """List news articles for an account.

        Args:
            account_id: Account ID

        Returns:
            List of news article dictionaries
        """
        result = await self._get(f"/accounts/{account_id}/news")
        return result.get("news", [])

    async def list_account_jobs(self, account_id: str) -> list[dict]:
        """List job postings for an account.

        Args:
            account_id: Account ID

        Returns:
            List of job posting dictionaries
        """
        result = await self._get(f"/accounts/{account_id}/job_postings")
        return result.get("job_postings", [])
