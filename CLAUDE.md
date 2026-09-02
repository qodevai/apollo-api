# qodev-apollo-api - Development Guidelines

## Development Workflow

All development tasks are managed via Makefile commands:

```bash
make install          # Install all dependencies (including dev)
make install-hooks    # Set up pre-commit hooks
make check           # Run all checks (lint, format, typecheck, typos)
make test            # Run tests with coverage
make lint            # Check code quality
make format          # Format code
make typecheck       # Run type checking
```

**Before committing:**
```bash
make check && make test
```

Pre-commit hooks will automatically run on commit, but it's faster to check manually first.

## Key Apollo API Learnings

### 1. Authentication

Apollo uses **`x-api-key` header** (NOT `Authorization: Bearer`):

```python
headers = {
    "x-api-key": "your_api_key",
    "Content-Type": "application/json",
}
```

### 2. Rate Limits (CRITICAL)

**Actual limits** discovered via response headers:
- **400 requests/hour** (primary bottleneck)
- 200 requests/minute
- 2,000 requests/day

Headers to monitor:
```
x-rate-limit-hourly: 400
x-hourly-requests-left: 399
x-rate-limit-minute: 200
x-minute-requests-left: 199
x-rate-limit-24-hour: 2000
x-24-hour-requests-left: 1999
```

**For sustained operations:**
- Use 10+ second delays between requests
- Monitor `x-hourly-requests-left`
- Stop if < 50 requests remaining
- Hourly limit is the bottleneck (not minute or daily)

### 3. Contact Search Strategies

**LinkedIn URL search:**
- Works for exact URL matches
- URLs change over time (custom URLs, profile updates)
- Always verify returned URL matches searched URL

**Name search:**
- Requires exact match
- No support for special characters (umlauts: ü, ö, ä, ß)
- Returns multiple people with same name → requires verification

**3-Tier Fallback Strategy:**
1. Search by LinkedIn URL (most reliable)
2. Fallback to name search (handles URL changes)
3. People database for auto-creation (if unique match)

**Success rate:** 77% with this strategy (23% not in Apollo database or ambiguous)

### 4. ProseMirror Notes Format

Apollo stores notes in ProseMirror JSON format. This library automatically converts to Markdown:

```json
{
  "type": "doc",
  "content": [
    {"type": "noteTitle", "content": [{"type": "text", "text": "Title"}]},
    {"type": "paragraph", "content": [{"type": "text", "text": "Content"}]}
  ]
}
```

→ Converted to clean Markdown by `prosemirror_to_markdown()` function.

**Known issue:** Apollo → HubSpot sync sends raw ProseMirror JSON instead of converting to text (Apollo's bug, not ours).

### 5. API Quirks

**Undocumented GET endpoints:**
- `GET /opportunity_pipelines` - Returns all pipelines (undocumented)
- `GET /opportunity_stages` - Returns all stages across pipelines (undocumented)

**People search limitations:**
- `linkedin_url` parameter is completely ignored (doesn't work)
- Must use `q_keywords` with name instead
- No umlaut support - transliterate names (Lübken → Luebken)

**LinkedIn URLs:**
- Change frequently when users update profiles
- Custom URLs can be added/removed
- Always normalize and verify matches

**`accounts/search` silently drops unknown filter keys:**
- Passing an unrecognised filter (e.g. `query=` instead of `q_organization_name=`) does **not** error — Apollo ignores it and returns an unfiltered default page (~28k accounts, "Google" first) that looks like a real match.
- This once caused a wrong company to be attached to a deal + a duplicate account.
- `search_accounts` guards against it: it validates `**filters` against `ACCOUNT_SEARCH_FILTERS` (`q_organization_name`, `account_stage_ids`, `account_label_ids`, `sort_by_field`, `sort_ascending`) and raises `ValueError` on unknown keys. Same silent-drop risk applies to the other `search_*` methods — pass only documented filters.

**Search-filter formats (empirically verified — a wrong format is silently ignored or matches nothing, never an error):**
- **Deal name search is `q_opportunity_name`, NOT `q_keywords`.** Apollo silently ignores `q_keywords` on `/opportunities/search` (a nonsense keyword returns *every* deal). `q_opportunity_name` is in `DEAL_SEARCH_FILTERS`; `q_keywords` is not (passing it raises).
- **`organization_num_employees_ranges`** (people): `"min,max"` **comma** strings, e.g. `["1,10"]`, `["1000,5000"]`. A dash (`"1-10"`) is silently ignored (returns baseline).
- **`person_seniorities`** (people): lowercase enums — `owner, founder, c_suite, partner, vp, head, director, manager, senior, entry, intern`. Uppercase / free text match 0 rows.
- **`person_locations` / `organization_locations`**: country name, 2-letter code (`"US"` == `"United States"`), or `"City, State, Country"`.
- **`revenue_range` / `organization_num_jobs_range`**: dict `{"min": int, "max": int}`. **`contact_email_status`**: `verified | unverified | likely to engage | unavailable`.
- **`contacts` `linkedin_url`**: must be Apollo's canonical form `http://www.linkedin.com/in/<slug>` (http, lowercased, url-encoded) or it matches nothing.
- Full per-filter formats live in each `search_*` docstring.

**`opportunities/update_roles` needs the role type NESTED under a `role` array:**
- Correct per-entry shape: `{"contact_id": …, "is_primary": …, "role": [{"opportunity_contact_role_type_id": …, "is_primary": …}]}`.
- Sending `opportunity_contact_role_type_id` flat on the entry (no `role` key) makes Apollo 422 with `undefined method 'map' for nil`.
- `update_opportunity_roles` reshapes the flat `RoleAssignment` entries into this wire format; callers still pass flat entries.
- The endpoint **replaces** the full role set and works with a normal (non-master) API key.
- **`opportunities/update_roles` can silently drop the write.** Live-observed: a set-role call returned 200 + the deal JSON with no error while the role was **not** persisted (a read-back minutes later showed 0 roles); the identical call succeeded on retry. `update_opportunity_roles` no longer trusts the write response — it always re-reads the opportunity afterwards and raises `RoleAssignmentError` if a requested role is missing from the read-back.

**Opportunity updates use `PATCH`, not `PUT`:**
- `update_opportunity(opportunity_id, **fields)` uses `PATCH /opportunities/{id}` (live-verified 2026-09-02) — unlike `update_contact`/`update_task`, which use `PUT`.

**`/notes/search` has its own per-endpoint daily quota, separate from the account-wide numbers you'd guess from other endpoints:**
- Live-observed (2026-09-02): `POST /notes/search` returned 429 with `x-24-hour-requests-left: 0` (Apollo's message named the internal route `meetings/api/v1/notes/finder`) while `/tasks`, `/contacts`, etc. on the same key still had budget. `GET /notes/{id}` is a **different** bucket (not exhausted at the same time).
- Since 0.6.0, `RateLimitError.endpoint` and `.limits` report exactly which endpoint/window ran out — check `.endpoint` before assuming account-wide throttling from a single 429.
- A report of `notes search --opportunity-id X` returning **0 items with no error** (not a 429) for a deal known to have notes could not be reproduced live during this investigation (the `/notes/search` daily quota was already exhausted by the time of testing). The client does not swallow non-2xx responses anywhere in the request path (verified via code review + a live repro of the 429 case above); if it recurs, capture `client.rate_limit_status` and the raw response alongside the empty result before assuming an index-lag bug on Apollo's side.

## Testing Strategy

### Unit Tests

Focus on:
1. **Model validation** - All models parse real API responses
2. **Utilities** - ProseMirror conversion, URL normalization
3. **Exceptions** - Custom error types with attributes

### Mock Strategy

```python
@pytest.fixture
def mock_httpx(mocker):
    mock_client = mocker.patch("qodev_apollo_api.client.httpx.AsyncClient")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"contacts": [...]}
    mock_response.headers = {"x-rate-limit-hourly": "400"}
    mock_client.return_value.request.return_value = mock_response
    return mock_client
```

### Integration Tests

Not included in library - each consuming project should test against Apollo's sandbox/test environment.

## Code Quality Standards

### Type Hints

All functions must have full type hints:

```python
async def search_contacts(
    self, page: int = 1, limit: int = 100, **filters
) -> PaginatedResponse[Contact]:
    ...
```

### Error Handling

Use custom exceptions:
- `AuthenticationError` - 401 responses
- `RateLimitError` - 429 responses (includes `retry_after`)
- `APIError` - Other errors (includes `status_code`)

### Pydantic Models

- Use `str | None` (not `Optional[str]`)
- Use `Field(default_factory=dict)` for dicts/lists
- All fields optional except `id` (for flexibility with partial API responses)

## Project Structure

```
qodev-apollo-api/
├── src/qodev_apollo_api/
│   ├── __init__.py      # Public API exports
│   ├── client.py        # ApolloClient class
│   ├── models.py        # Pydantic models
│   ├── exceptions.py    # Custom exceptions
│   └── utils.py         # Utility functions
├── tests/
│   ├── test_client.py
│   ├── test_models.py
│   ├── test_exceptions.py
│   └── test_utils.py
├── pyproject.toml       # Package configuration
├── Makefile             # Development commands
├── .github/workflows/   # CI/CD pipelines
├── .pre-commit-config.yaml
├── README.md
├── CLAUDE.md
└── LICENSE
```

## CI/CD Pipeline

GitHub Actions runs on push to main and PRs:

**Lint jobs** (parallel):
- lint (ruff check + format check)
- typecheck (pyright)

**Test job:**
- pytest with coverage

**Publish** (on tag push, gated on lint + typecheck + test):
- Trusted Publishers (OIDC) to PyPI

## Common Pitfalls

1. **Forgetting context manager** - Always use `async with ApolloClient()`
2. **Ignoring rate limits** - Monitor headers, especially hourly limit
3. **Trusting LinkedIn URLs** - Always verify returned URLs match
4. **Name search without verification** - Multiple people can have same name
5. **Not handling optional fields** - All fields except `id` can be None

## Migration from Existing Implementations

When migrating from old implementations:

1. **Import changes:**
   ```python
   from qodev_apollo_api import ApolloClient
   ```

2. **Model changes:**
   ```python
   # Old: ContactSummary, ContactDetail
   # New: Contact (unified model)

   # Old
   contact: ContactDetail = await client.get_contact(id)

   # New
   contact: Contact = await client.get_contact(id)
   ```

3. **Response types:**
   ```python
   # All search methods now return PaginatedResponse[T]
   result = await client.search_contacts(limit=10)
   for contact in result.items:  # .items, not .contacts
       print(contact.name)
   ```

## Useful Resources

- [Apollo.io API Docs](https://apolloio.github.io/apollo-api-docs/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
