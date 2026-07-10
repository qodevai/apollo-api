"""Apollo API Client.

Type-safe async wrapper for Apollo.io API.
"""

import logging
import os
from datetime import datetime
from types import TracebackType
from typing import Any

import httpx
from pydantic import ValidationError

from .exceptions import APIError, AuthenticationError, RateLimitError
from .models import (
    Account,
    AccountDetail,
    CalendarEvent,
    Call,
    Contact,
    ContactDetail,
    Conversation,
    ConversationDetail,
    CustomField,
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
    RoleAssignment,
    SortOrder,
    Stage,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
    resolve_task,
)
from .utils import markdown_to_prosemirror, normalize_linkedin_url, prosemirror_to_markdown

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search-filter allowlists
#
# Apollo's /search endpoints *silently drop* unrecognised filter keys and return
# an unfiltered default page that looks like a real match (e.g. a typo'd
# ``query=`` on accounts returned ~28k rows, "Google" first). To stop that, each
# search method validates its ``**filters`` against the relevant allowlist below.
#
# Endpoints with a documented, stable flat-filter vocabulary are validated
# *strictly* (raise on unknown). The activity endpoints below have no published
# filter docs, so an over-tight allowlist would reject valid filters — those are
# validated *leniently* (log a warning, still send the request). See
# ``_validate_search_filters``.
# ---------------------------------------------------------------------------

# Strict (raise on unknown) — documented flat-filter endpoints.
ACCOUNT_SEARCH_FILTERS = frozenset(
    {
        "q_organization_name",
        "account_stage_ids",
        "account_label_ids",
        "sort_by_field",
        "sort_ascending",
    }
)
CONTACT_SEARCH_FILTERS = frozenset(
    {
        "q_keywords",
        "contact_stage_ids",
        "contact_label_ids",
        "linkedin_url",
        "sort_by_field",
        "sort_ascending",
    }
)
DEAL_SEARCH_FILTERS = frozenset(
    {
        # Deal *name* search is q_opportunity_name — NOT q_keywords, which Apollo
        # silently ignores for /opportunities/search (verified: a nonsense keyword
        # still returned every deal).
        "q_opportunity_name",
        "opportunity_stage_ids",
        "sort_by_field",
        "sort_ascending",
    }
)
# search_people passes *everything* (incl. page/per_page) through **filters, so
# those are part of the allowlist here (unlike the methods with explicit args).
PEOPLE_SEARCH_FILTERS = frozenset(
    {
        "q_keywords",
        "person_titles",
        "include_similar_titles",
        "person_seniorities",
        "person_locations",
        "organization_locations",
        "organization_ids",
        "organization_num_employees_ranges",
        "q_organization_domains_list",
        "revenue_range",
        "currently_using_all_of_technology_uids",
        "currently_using_any_of_technology_uids",
        "currently_not_using_any_of_technology_uids",
        "q_organization_job_titles",
        "organization_job_locations",
        "organization_num_jobs_range",
        "organization_job_posted_at_range",
        "contact_email_status",
        "page",
        "per_page",
    }
)

# Lenient (warn on unknown) — undocumented activity endpoints. Seeded from known
# usage; incompleteness only costs a log line, never a broken call.
NOTE_SEARCH_FILTERS = frozenset({"contact_ids", "account_ids", "opportunity_ids", "q_keywords"})
CALL_SEARCH_FILTERS = frozenset({"contact_ids", "account_ids", "user_ids", "q_keywords"})
TASK_SEARCH_FILTERS = frozenset({"contact_ids", "account_ids", "opportunity_ids", "q_keywords"})
EMAIL_SEARCH_FILTERS = frozenset({"contact_ids", "emailer_campaign_ids", "q_keywords"})
CONVERSATION_SEARCH_FILTERS = frozenset({"q_keywords"})
CALENDAR_EVENT_SEARCH_FILTERS = frozenset({"contact_ids", "user_ids", "q_keywords"})


def _validate_search_filters(
    filters: dict, allowed: frozenset[str], resource: str, *, strict: bool
) -> None:
    """Guard against Apollo silently dropping unknown ``**filters`` keys.

    Apollo ignores unrecognised keys on its /search endpoints and returns an
    unfiltered default page that looks like a real match. When ``strict``, raise
    ``ValueError`` on any unknown key (documented endpoints); otherwise log a
    warning and let the request through (undocumented endpoints, where the full
    valid set isn't published and a hard allowlist would reject valid filters).
    """
    unknown = set(filters) - allowed
    if not unknown:
        return
    # Strict allowlists are authoritative ("Supported filters"); lenient ones are
    # seeded from known usage and may be incomplete ("Known filters"), so the
    # wording doesn't imply the warned-about key is definitely invalid.
    label = "Supported filters" if strict else "Known filters"
    msg = (
        f"Unknown {resource} search filter(s): {', '.join(sorted(unknown))}. "
        f"Apollo silently ignores unrecognised keys and returns an unfiltered "
        f"default page. {label}: {', '.join(sorted(allowed))}."
    )
    if strict:
        raise ValueError(msg)
    logger.warning(msg)


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
                "hourly_limit": int(headers.get("x-rate-limit-hourly") or 0),
                "hourly_left": int(headers.get("x-hourly-requests-left") or 0),
                "minute_limit": int(headers.get("x-rate-limit-minute") or 0),
                "minute_left": int(headers.get("x-minute-requests-left") or 0),
                "daily_limit": int(headers.get("x-rate-limit-24-hour") or 0),
                "daily_left": int(headers.get("x-24-hour-requests-left") or 0),
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

    async def _put(self, endpoint: str, data: dict) -> dict:
        """Make PUT request."""
        return await self._request("PUT", endpoint, json=data)

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
            **filters: Contact search filters (see ``CONTACT_SEARCH_FILTERS``):

                - ``q_keywords`` (str): free-text over name / title / company / email.
                - ``contact_stage_ids`` (list[str]): stage IDs (see ``get_contact_stages``).
                - ``contact_label_ids`` (list[str]): label / list IDs.
                - ``linkedin_url`` (str): must be Apollo's **canonical** form —
                  ``http://www.linkedin.com/in/<slug>`` (http, lowercased,
                  url-encoded). A near-miss silently matches nothing.
                - ``sort_by_field`` (str): ``contact_last_activity_date`` |
                  ``contact_email_last_opened_at`` | ``contact_email_last_clicked_at`` |
                  ``contact_created_at`` | ``contact_updated_at``.
                - ``sort_ascending`` (bool).

        Returns:
            Paginated response with Contact items
        """
        _validate_search_filters(filters, CONTACT_SEARCH_FILTERS, "contact", strict=True)
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/contacts/search", data)

        contacts = [Contact.model_validate(c) for c in result.get("contacts", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Contact](
            items=contacts,
            total=pagination.get("total_entries", len(contacts)),
            page=page,
        )

    async def get_contact(self, contact_id: str) -> ContactDetail:
        """Get contact details by ID.

        Args:
            contact_id: Contact ID

        Returns:
            ContactDetail model (includes employment_history and other detail-only fields)
        """
        result = await self._get(f"/contacts/{contact_id}")
        return ContactDetail.model_validate(result.get("contact", {}))

    async def create_contact(
        self,
        first_name: str,
        last_name: str,
        **fields,
    ) -> Contact:
        """Create a new contact.

        Args:
            first_name: Contact first name
            last_name: Contact last name
            **fields: Additional fields (email, title, company_name, linkedin_url, etc.)

        Returns:
            Created Contact model
        """
        data = {
            "first_name": first_name,
            "last_name": last_name,
            **fields,
        }
        result = await self._post("/contacts", data)
        return Contact.model_validate(result.get("contact", result))

    async def update_contact(self, contact_id: str, **fields) -> Contact:
        """Update a contact's fields.

        Args:
            contact_id: Contact ID
            **fields: Fields to update (e.g., label_ids, title, etc.)

        Returns:
            Updated Contact model
        """
        result = await self._put(f"/contacts/{contact_id}", fields)
        return Contact.model_validate(result.get("contact", {}))

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
        """Find an existing contact by LinkedIn URL (2-tier lookup).

        Strategy:
        1. Search existing contacts by LinkedIn URL (exact match).
        2. Fall back to a name search among existing contacts (unique match whose
           normalized URL equals the target).

        Auto-creation from Apollo's people database (the former Step 3) is no
        longer possible: ``/mixed_people/api_search`` returns teaser data only
        (no ``linkedin_url``, an obfuscated last name, no email), so a URL match
        can never succeed and there isn't enough data to create a usable contact.

        Args:
            linkedin_url: LinkedIn profile URL
            person_name: Person's full name (for the fallback search)
            create_if_missing: Deprecated no-op — retained for backwards
                compatibility. Logs a warning when set; never creates a contact.
            contact_stage_id: Deprecated no-op (was only used for auto-creation).

        Returns:
            Contact ID if found, None otherwise.
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

        # Auto-creation from the people database is no longer possible — Apollo's
        # /mixed_people/api_search returns teaser data (no linkedin_url, obfuscated
        # last name, no email), so a URL match can't be made nor a usable contact
        # created. Warn instead of silently doing nothing.
        if create_if_missing and person_name:
            logger.warning(
                "find_contact_by_linkedin_url: create_if_missing is no longer supported — "
                "Apollo's people search returns teaser data without linkedin_url, so no "
                "contact was created for %r. Use enrichment/reveal + create_contact instead.",
                person_name,
            )

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
            **filters: Account search filters (see ``ACCOUNT_SEARCH_FILTERS``):

                - ``q_organization_name`` (str): company-name keyword.
                - ``account_stage_ids`` (list[str]): account stage IDs.
                - ``account_label_ids`` (list[str]): label / list IDs.
                - ``sort_by_field`` (str): ``account_last_activity_date`` |
                  ``account_created_at`` | ``account_updated_at``.
                - ``sort_ascending`` (bool).

        Returns:
            Paginated response with Account items

        Raises:
            ValueError: If an unrecognised filter key is passed. Apollo silently
                ignores unknown keys and returns an unfiltered default page (which
                looks like a real match), so we fail loudly instead of returning the
                wrong accounts. Note ``query=`` is **not** a valid filter — use
                ``q_organization_name=`` to search by name.
        """
        _validate_search_filters(filters, ACCOUNT_SEARCH_FILTERS, "account", strict=True)
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/accounts/search", data)

        accounts = [Account.model_validate(a) for a in result.get("accounts", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Account](
            items=accounts,
            total=pagination.get("total_entries", len(accounts)),
            page=page,
        )

    async def get_account(self, account_id: str) -> AccountDetail:
        """Get account details by ID.

        Args:
            account_id: Account ID

        Returns:
            AccountDetail model (includes enrichment data, tech stack, org chart, etc.)
        """
        result = await self._get(f"/accounts/{account_id}")
        return AccountDetail.model_validate(result.get("account", {}))

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
            **filters: Deal search filters (see ``DEAL_SEARCH_FILTERS``):

                - ``q_opportunity_name`` (str): deal-name keyword. **Use this, not
                  ``q_keywords``** — Apollo silently ignores ``q_keywords`` on
                  ``/opportunities/search`` (it returns every deal).
                - ``opportunity_stage_ids`` (list[str]): deal stage IDs (see
                  ``list_all_stages``).
                - ``sort_by_field`` (str): ``amount`` | ``is_closed`` | ``is_won``.
                - ``sort_ascending`` (bool).

        Returns:
            Paginated response with Deal items
        """
        _validate_search_filters(filters, DEAL_SEARCH_FILTERS, "deal", strict=True)
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

    async def create_deal(self, name: str, **fields) -> Deal:
        """Create a new deal/opportunity.

        Note:
            Apollo requires a **master** API key for this endpoint; a non-master
            key returns 403. ``name`` is the only required field.

        Args:
            name: Human-readable deal name (required).
            **fields: Additional fields (owner_id, account_id, amount,
                opportunity_stage_id, closed_date [YYYY-MM-DD], etc.).

        Returns:
            The created Deal model.
        """
        data = {"name": name, **fields}
        result = await self._post("/opportunities", data)
        return Deal.model_validate(result.get("opportunity", result))

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

    async def list_all_stages(self) -> PaginatedResponse[Stage]:
        """List all pipeline stages across all pipelines.

        Returns:
            Paginated response with all Stage items (unfiltered)
        """
        result = await self._get("/opportunity_stages")
        stages = [Stage.model_validate(s) for s in result.get("opportunity_stages", [])]

        return PaginatedResponse[Stage](
            items=stages,
            total=len(stages),
            page=1,
        )

    async def list_opportunity_contact_role_types(
        self,
    ) -> PaginatedResponse[OpportunityContactRoleType]:
        """List all opportunity contact role types (undocumented endpoint).

        Returns role type definitions (e.g., Decision Maker, Buyer, Champion)
        that map to OpportunityRoleEntry.opportunity_contact_role_type_id.

        Returns:
            Paginated response with OpportunityContactRoleType items
        """
        result = await self._post("/opportunity_contact_role_types/search", {})
        role_types = [
            OpportunityContactRoleType.model_validate(rt)
            for rt in result.get("opportunity_contact_role_types", [])
        ]
        return PaginatedResponse[OpportunityContactRoleType](
            items=role_types,
            total=len(role_types),
            page=1,
        )

    async def update_opportunity_roles(
        self, opportunity_id: str, roles: list[RoleAssignment]
    ) -> Deal:
        """Set the contact roles on a deal/opportunity (undocumented endpoint).

        This **replaces** the full set of contact roles on the opportunity, so
        callers should pass the complete desired set (read the current roles from
        ``get_deal(...).opportunity_contact_roles`` and modify them). Each entry is
        a dict with ``contact_id`` and, optionally, ``opportunity_contact_role_type_id``
        and ``is_primary``::

            roles = [
                {"contact_id": "abc", "opportunity_contact_role_type_id": "t1", "is_primary": True},
                {"contact_id": "def", "is_primary": False},
            ]

        Args:
            opportunity_id: The opportunity/deal ID.
            roles: The complete list of contact-role entries to set.

        Returns:
            The updated Deal.
        """
        # Apollo's endpoint expects each entry's role type *nested* under a ``role``
        # array — sending ``opportunity_contact_role_type_id`` flat on the entry (with
        # no ``role`` key) makes the server call ``.map`` on nil and 422 with
        # "undefined method 'map' for nil". Reshape the flat RoleAssignment entries
        # into the wire format the server actually accepts.
        wire_roles: list[dict] = []
        for entry in roles:
            # RoleAssignment types is_primary as a bool; default to False when omitted.
            # Avoid bool(...) coercion, which would turn a stray truthy non-bool (e.g.
            # the string "false") into True.
            is_primary = entry.get("is_primary", False)
            role_obj: dict[str, Any] = {"is_primary": is_primary}
            role_type_id = entry.get("opportunity_contact_role_type_id")
            if role_type_id:
                role_obj["opportunity_contact_role_type_id"] = role_type_id
            wire_roles.append(
                {"contact_id": entry["contact_id"], "is_primary": is_primary, "role": [role_obj]}
            )

        data = {"opportunity_id": opportunity_id, "roles": wire_roles}
        result = await self._post("/opportunities/update_roles", data)
        return Deal.model_validate(result.get("opportunity", result))

    # ========================================================================
    # CUSTOM FIELDS
    # ========================================================================

    async def list_custom_fields(self) -> list[CustomField]:
        """List all typed custom field definitions (undocumented endpoint).

        Returns definitions for custom fields across every modality (contact,
        account, opportunity). Use ``modality`` to filter client-side.

        Returns:
            List of CustomField definitions.
        """
        result = await self._get("/typed_custom_fields")
        return [CustomField.model_validate(f) for f in result.get("typed_custom_fields", [])]

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

        Uses ``/mixed_people/api_search``; the older ``/mixed_people/search`` is
        deprecated for API callers (returns 422). Note that this endpoint returns
        **teaser data only** — ``first_name``, ``last_name_obfuscated``, ``title``
        and ``organization``, but not full name / email / linkedin_url (those
        require a separate enrichment/reveal step and consume credits).

        Args:
            **filters: People search filters (see ``PEOPLE_SEARCH_FILTERS``).
                Formats matter — a wrong format is silently ignored or matches
                nothing rather than erroring:

                - ``q_keywords`` (str): free text.
                - ``person_titles`` (list[str]): job titles, e.g. ``["CEO", "VP Sales"]``.
                  ``include_similar_titles`` (bool): broaden to related titles.
                - ``person_seniorities`` (list[str]): **lowercase enums** —
                  ``owner, founder, c_suite, partner, vp, head, director, manager,
                  senior, entry, intern``. Uppercase / free text (``"VP"``,
                  ``"vice president"``) match **0** rows.
                - ``person_locations`` / ``organization_locations`` (list[str]):
                  person / company location. Accepts a country name, a 2-letter
                  country code (``"US"`` == ``"United States"``), or
                  ``"City, State, Country"``.
                - ``organization_num_employees_ranges`` (list[str]): company-size
                  buckets as **"min,max"** strings, e.g. ``["1,10"]``,
                  ``["1000,5000"]``. A dash (``"1-10"``) is **silently ignored**.
                - ``q_organization_domains_list`` (list[str]): company domains,
                  e.g. ``["acme.com"]``. ``organization_ids`` (list[str]): Apollo org IDs.
                - ``contact_email_status`` (list[str]): ``verified``, ``unverified``,
                  ``likely to engage``, ``unavailable``.
                - ``revenue_range`` / ``organization_num_jobs_range`` (dict):
                  ``{"min": int, "max": int}``.
                - ``organization_job_posted_at_range`` (dict): ``{"min": "YYYY-MM-DD",
                  "max": "YYYY-MM-DD"}``.
                - ``currently_using_any_of_technology_uids`` /
                  ``currently_using_all_of_technology_uids`` /
                  ``currently_not_using_any_of_technology_uids`` (list[str]): tech
                  UIDs, e.g. ``["salesforce"]``.
                - ``q_organization_job_titles`` (list[str]),
                  ``organization_job_locations`` (list[str]).
                - ``page`` / ``per_page`` (int): pagination (this method has no
                  explicit page/limit args — pass them as filters).

        Returns:
            Raw Apollo response dict: ``people`` (list) and ``total_entries`` (int).
        """
        _validate_search_filters(filters, PEOPLE_SEARCH_FILTERS, "people", strict=True)
        return await self._post("/mixed_people/api_search", filters)

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
        _validate_search_filters(filters, NOTE_SEARCH_FILTERS, "note", strict=False)
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/notes/search", data)

        notes = []
        for note_data in result.get("notes", []):
            # Convert ProseMirror JSON to Markdown, pass as overrides (don't mutate original)
            content_json = note_data.get("content", "{}")
            title, markdown = prosemirror_to_markdown(content_json)

            notes.append(Note.model_validate({**note_data, "title": title, "content": markdown}))

        pagination = result.get("pagination", {})
        return PaginatedResponse[Note](
            items=notes,
            total=pagination.get("total_entries", len(notes)),
            page=page,
        )

    async def create_note(
        self,
        content: str,
        title: str | None = None,
        *,
        contact_ids: list[str] | None = None,
        account_ids: list[str] | None = None,
        opportunity_ids: list[str] | None = None,
    ) -> dict:
        """Create a note.

        Apollo stores note bodies in the ``content`` field as ProseMirror JSON,
        so the plain text / Markdown ``content`` is converted via
        :func:`~qodev_apollo_api.utils.markdown_to_prosemirror` before posting.
        (Posting ``{"note": <plaintext>}`` is silently ignored by Apollo and
        produces an empty note.)

        Args:
            content: Note body as plain text / Markdown.
            title: Optional note title (rendered as the ProseMirror noteTitle).
            contact_ids: List of contact IDs to associate
            account_ids: List of account IDs to associate
            opportunity_ids: List of opportunity IDs to associate

        Returns:
            Raw API response with created note data
        """
        data: dict[str, str | list[str]] = {
            "content": markdown_to_prosemirror(content, title=title)
        }
        if contact_ids:
            data["contact_ids"] = contact_ids
        if account_ids:
            data["account_ids"] = account_ids
        if opportunity_ids:
            data["opportunity_ids"] = opportunity_ids

        return await self._post("/notes", data)

    async def delete_note(self, note_id: str) -> dict:
        """Delete a note by ID.

        Args:
            note_id: Apollo note ID.

        Returns:
            Raw API response.
        """
        return await self._request("DELETE", f"/notes/{note_id}")

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
        _validate_search_filters(filters, CALL_SEARCH_FILTERS, "call", strict=False)
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
        self,
        page: int = 1,
        limit: int = 100,
        task_type_cds: list[TaskType | str] | None = None,
        user_ids: list[str] | None = None,
        sort: list[tuple[str, SortOrder]] | None = None,
        **filters,
    ) -> PaginatedResponse[Task]:
        """Search task activities.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            task_type_cds: Filter by task type codes. Valid values:
                call, account_call, contact_call, outreach_manual_email,
                linkedin_step_connect, linkedin_step_message,
                linkedin_step_interact_post, linkedin_step_view_profile,
                linkedin_actions, contact_action_item, account_action_item
            user_ids: Filter by owner user IDs
            sort: Sort order as list of (field, direction) tuples, e.g.
                [("task_priority", SortOrder.ASC), ("task_due_at", SortOrder.ASC)]
            **filters: Additional filters

        Returns:
            Paginated response with specific Task subclass items
        """
        _validate_search_filters(filters, TASK_SEARCH_FILTERS, "task", strict=False)
        data: dict[str, Any] = {"page": page, "per_page": min(limit, 100), **filters}
        if task_type_cds is not None:
            data["task_type_cds"] = task_type_cds
        if user_ids is not None:
            data["user_ids"] = user_ids
        if sort is not None:
            data["multi_sort"] = [{field: {"order": order}} for field, order in sort]
        result = await self._post("/tasks/search", data)

        tasks: list[Task] = []
        for raw in result.get("tasks") or []:
            if not isinstance(raw, dict):
                # A non-dict row (e.g. a stray null) would make resolve_task raise
                # AttributeError, not ValidationError — skip it before we get there.
                logger.warning("Skipping non-dict task row: %r", raw)
                continue
            try:
                tasks.append(resolve_task(raw))
            except ValidationError:
                # A single structurally-invalid row (e.g. missing id) must not sink the whole
                # page — skip it so the rest of the results stay usable.
                logger.warning("Skipping unparseable task id=%s", raw.get("id"), exc_info=True)
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
        _validate_search_filters(filters, EMAIL_SEARCH_FILTERS, "email", strict=False)
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
        type: TaskType | str = TaskType.CONTACT_ACTION_ITEM,
        priority: TaskPriority | str = TaskPriority.MEDIUM,
        **fields,
    ) -> Task:
        """Create a task.

        Args:
            contact_ids: List of contact IDs
            note: Task description
            type: Task type
            priority: Task priority
            **fields: Additional fields (due_at, status, etc.)

        Returns:
            Created Task subclass matching the task type
        """
        if not contact_ids:
            raise ValueError("contact_ids must not be empty")
        data = {
            "contact_ids": contact_ids,
            "note": note,
            "type": type,
            "priority": priority,
            **fields,
        }
        result = await self._post("/tasks", data)
        return resolve_task(result.get("task", result))

    async def complete_task(self, task_id: str, note: str | None = None) -> Task:
        """Mark a task as completed.

        Args:
            task_id: Task ID to complete
            note: Optional note/message to attach on completion

        Returns:
            Completed Task model
        """
        data: dict[str, Any] = {}
        if note is not None:
            data["note"] = note
        result = await self._post(f"/tasks/{task_id}/complete", data)
        return resolve_task(result.get("task", result))

    async def get_task(self, task_id: str) -> Task:
        """Get task details by ID.

        Args:
            task_id: Task ID

        Returns:
            Task model
        """
        result = await self._get(f"/tasks/{task_id}")
        return resolve_task(result.get("task", {}))

    async def create_email_task(
        self,
        contact_ids: list[str],
        note: str,
        user_id: str | None = None,
        priority: TaskPriority | str = TaskPriority.MEDIUM,
        due_at: datetime | None = None,
        **fields,
    ) -> EmailTask:
        """Create an email task (Manual E-Mail type).

        Creates a task of type 'outreach_manual_email' associated with contacts.
        The task is created with status='scheduled' which triggers Apollo to
        auto-create an emailer_message companion object. Use
        update_emailer_message() to set the email subject and body afterwards.

        After setting the email content with update_emailer_message(), call
        send_email_task() to send the email immediately.

        Args:
            contact_ids: List of contact IDs to associate
            note: Task title/description
            user_id: User ID to assign the task to (optional)
            priority: Task priority (default: medium)
            due_at: When the task is due (optional).
                Pass at creation time so it propagates to the emailer_message.
            **fields: Additional task fields

        Returns:
            Created EmailTask model (includes emailer_message)
        """
        extra: dict[str, Any] = {**fields}
        if user_id is not None:
            extra["user_id"] = user_id
        if due_at is not None:
            extra["due_at"] = due_at.isoformat()
        data = {
            "contact_ids": contact_ids,
            "note": note,
            "type": TaskType.OUTREACH_MANUAL_EMAIL,
            "priority": priority,
            "status": TaskStatus.SCHEDULED,
            **extra,
        }
        result = await self._post("/tasks", data)
        return EmailTask.model_validate(result.get("task", result))

    async def create_linkedin_connect_task(
        self,
        contact_id: str,
        title: str,
        message: str,
        note: str = "",
        user_id: str | None = None,
        priority: TaskPriority | str = TaskPriority.MEDIUM,
        due_at: datetime | None = None,
        **fields,
    ) -> LinkedInConnectTask:
        """Create a LinkedIn connection request task with a message.

        Creates a task of type 'linkedin_step_connect' that sends a
        connection request with a personalized message via Apollo.

        Args:
            contact_id: Contact ID to send the connection request to
            title: Task title (e.g. "Connect Alexis Kartmann")
            message: The connection request message the recipient sees
            note: Internal task description (default: empty)
            user_id: User ID to assign the task to (optional)
            priority: Task priority (default: medium)
            due_at: When the task is due
                (optional, defaults to now)
            **fields: Additional task fields

        Returns:
            Created LinkedInConnectTask model
        """
        extra: dict[str, Any] = {**fields}
        if user_id is not None:
            extra["user_id"] = user_id
        if due_at is not None:
            extra["due_at"] = due_at.isoformat()
        extra["title"] = title
        extra["contact_id"] = contact_id
        extra["standalone_outreach_task_message"] = {
            "body_text": message,
            "subject": "",
        }
        data = {
            "contact_ids": [contact_id],
            "note": note,
            "type": TaskType.LINKEDIN_STEP_CONNECT,
            "priority": priority,
            "status": TaskStatus.SCHEDULED,
            **extra,
        }
        result = await self._post("/tasks", data)
        return LinkedInConnectTask.model_validate(result.get("task", result))

    async def create_linkedin_message_task(
        self,
        contact_id: str,
        title: str,
        message: str,
        note: str = "",
        user_id: str | None = None,
        priority: TaskPriority | str = TaskPriority.MEDIUM,
        due_at: datetime | None = None,
        **fields,
    ) -> LinkedInMessageTask:
        """Create a LinkedIn message task.

        Creates a task of type 'linkedin_step_message' that sends a
        LinkedIn message to an existing connection via Apollo.

        Args:
            contact_id: Contact ID to send the message to
            title: Task title
            message: The LinkedIn message body the recipient sees
            note: Internal task description (default: empty)
            user_id: User ID to assign the task to (optional)
            priority: Task priority (default: medium)
            due_at: When the task is due
                (optional)
            **fields: Additional task fields

        Returns:
            Created LinkedInMessageTask model
        """
        extra: dict[str, Any] = {**fields}
        if user_id is not None:
            extra["user_id"] = user_id
        if due_at is not None:
            extra["due_at"] = due_at.isoformat()
        extra["title"] = title
        extra["contact_id"] = contact_id
        extra["standalone_outreach_task_message"] = {
            "body_text": message,
            "subject": "",
        }
        data = {
            "contact_ids": [contact_id],
            "note": note,
            "type": TaskType.LINKEDIN_STEP_MESSAGE,
            "priority": priority,
            "status": TaskStatus.SCHEDULED,
            **extra,
        }
        result = await self._post("/tasks", data)
        return LinkedInMessageTask.model_validate(result.get("task", result))

    async def skip_tasks(self, task_ids: list[str]) -> dict:
        """Skip (archive) one or more tasks.

        Args:
            task_ids: List of task IDs to skip

        Returns:
            Raw API response
        """
        data = {
            "ids": task_ids,
            "on_task_page": True,
            "async": False,
        }
        return await self._post("/tasks/bulk_skip", data)

    async def update_task(self, task_id: str, **fields) -> Task:
        """Update a task's fields.

        Updates task-level properties like priority, due_at, or note.
        To modify the email subject/body on email tasks, use
        update_emailer_message() instead.

        Args:
            task_id: Task ID to update
            **fields: Fields to update (priority, due_at, note, etc.)

        Returns:
            Updated Task model
        """
        if not fields:
            raise ValueError("At least one field must be provided")
        result = await self._put(f"/tasks/{task_id}", fields)
        return resolve_task(result.get("task", {}))

    async def update_emailer_message(
        self,
        message_id: str,
        subject: str | None = None,
        body_html: str | None = None,
        **fields,
    ) -> EmailerMessage:
        """Update an emailer message's subject and body.

        Email tasks have a companion emailer_message object that holds the
        email content. Use this method to set the subject and body after
        creating an email task with create_email_task().

        The message_id can be found in the task's emailer_message.id field.

        Args:
            message_id: Emailer message ID (from task.emailer_message.id)
            subject: Email subject line (optional)
            body_html: Email body as HTML (optional). Note: body_text is
                auto-derived from body_html by the API.
            **fields: Additional fields (cc_emails, bcc_emails, etc.)

        Returns:
            Updated EmailerMessage model
        """
        data: dict[str, Any] = {**fields}
        if subject is not None:
            data["subject"] = subject
        if body_html is not None:
            data["body_html"] = body_html
        if not data:
            raise ValueError("At least one field must be provided")
        result = await self._put(f"/emailer_messages/{message_id}", data)
        return EmailerMessage.model_validate(result.get("emailer_message", result))

    async def send_email_task(
        self,
        emailer_message_id: str,
    ) -> EmailerMessage:
        """Send an email task immediately.

        Transitions the emailer_message from 'drafted' to 'scheduled' for
        immediate async sending, and marks the parent task as completed.

        Args:
            emailer_message_id: Emailer message ID (from task.emailer_message.id)

        Returns:
            Sent EmailerMessage model
        """
        result = await self._post(
            f"/emailer_messages/{emailer_message_id}/send_now",
            {"surface": "tasks"},
        )
        return EmailerMessage.model_validate(result.get("emailer_message", result))

    async def list_contact_tasks(self, contact_id: str) -> list[Task]:
        """List tasks for a contact.

        Apollo removed the ``/contacts/{id}/tasks`` sub-resource route (now 404),
        so this filters the tasks search by ``contact_ids`` instead.

        Args:
            contact_id: Contact ID

        Returns:
            List of Task subclasses matching each task's type
        """
        result = await self.search_tasks(contact_ids=[contact_id])
        return result.items

    # ========================================================================
    # CALENDAR EVENTS
    # ========================================================================

    async def search_calendar_events(
        self, page: int = 1, limit: int = 100, **filters
    ) -> PaginatedResponse[CalendarEvent]:
        """Search calendar events.

        Args:
            page: Page number (default 1)
            limit: Results per page (default 100, max 100)
            **filters: Additional filters

        Returns:
            Paginated response with CalendarEvent items
        """
        _validate_search_filters(
            filters, CALENDAR_EVENT_SEARCH_FILTERS, "calendar event", strict=False
        )
        data = {"page": page, "per_page": min(limit, 100), **filters}
        result = await self._post("/calendar_events/search", data)

        events = [CalendarEvent.model_validate(e) for e in result.get("calendar_events", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[CalendarEvent](
            items=events,
            total=pagination.get("total_entries", len(events)),
            page=page,
        )

    # ========================================================================
    # CONVERSATIONS
    # ========================================================================

    async def search_conversations(
        self, page: int = 1, limit: int = 25, **filters
    ) -> PaginatedResponse[Conversation]:
        """Search recorded conversations (Zoom/Teams/Meet).

        Args:
            page: Page number (default 1)
            limit: Results per page (default 25, max 25)
            **filters: Additional filters

        Returns:
            Paginated response with Conversation items
        """
        _validate_search_filters(filters, CONVERSATION_SEARCH_FILTERS, "conversation", strict=False)
        data = {"page": page, "per_page": min(limit, 25), **filters}
        result = await self._post("/conversations/search", data)

        conversations = [Conversation.model_validate(c) for c in result.get("conversations", [])]
        pagination = result.get("pagination", {})

        return PaginatedResponse[Conversation](
            items=conversations,
            total=pagination.get("total_entries", len(conversations)),
            page=page,
        )

    async def get_conversation(self, conversation_id: str) -> ConversationDetail:
        """Get conversation details by ID (includes transcript and summary).

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationDetail model (includes transcript, call_summary, video_recording)
        """
        result = await self._get(f"/conversations/{conversation_id}")
        # Conversations detail API returns data at top level (no wrapping key)
        return ConversationDetail.model_validate(result)

    # ========================================================================
    # NEWS & JOBS
    # ========================================================================

    async def list_account_jobs(self, account_id: str) -> list[dict]:
        """List job postings for an account.

        Apollo removed the ``/accounts/{id}/job_postings`` sub-resource route (now
        404). Job postings live on the linked *organization*, so this resolves the
        account's ``organization_id`` and reads ``/organizations/{org_id}/job_postings``.

        Args:
            account_id: CRM account ID (its linked organization holds the postings).

        Returns:
            List of job posting dictionaries (empty if the account has no linked
            organization).
        """
        account = await self.get_account(account_id)
        if not account.organization_id:
            return []
        result = await self._get(f"/organizations/{account.organization_id}/job_postings")
        return result.get("organization_job_postings", [])

    # ========================================================================
    # USAGE & RATE LIMITS
    # ========================================================================

    async def get_api_usage(self) -> dict[str, dict]:
        """Get API usage stats across all endpoints.

        Returns:
            Dictionary keyed by endpoint (e.g. '["api/v1/accounts", "search"]')
            with day/hour/minute limits, consumed, and left_over counts.
        """
        return await self._post("/usage_stats/api_usage_stats", {})
