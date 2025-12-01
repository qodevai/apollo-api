# Apollo Client - Development Guidelines

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
    mock_client = mocker.patch("apollo.client.httpx.AsyncClient")
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
apollo-client/
├── src/apollo/
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
├── .gitlab-ci.yml       # CI pipeline
├── .pre-commit-config.yaml
├── README.md
├── CLAUDE.md
└── LICENSE
```

## CI/CD Pipeline

GitLab CI runs on MR and main branch:

**Lint stage** (parallel):
- lint (ruff)
- typecheck (pyright)
- typos (spell check)
- format-check (ruff format)

**Test stage:**
- pytest with coverage (requires >80%)

All jobs use Makefile commands → local dev matches CI exactly.

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
   # Old
   from apollo.client import ApolloClient

   # New
   from apollo import ApolloClient
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
