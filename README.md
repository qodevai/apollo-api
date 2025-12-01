# Apollo Client

Async Python client for Apollo.io CRM API with full type safety.

## Features

- **Async-first design** with httpx
- **Full Pydantic v2 models** for type safety
- **Context manager support** for clean resource management
- **Intelligent contact matching** with 3-tier fallback strategy
- **Built-in rate limit tracking** (400/hour, 200/min, 2000/day)
- **40+ API methods** across 8 endpoint groups
- **Comprehensive error handling** with custom exceptions
- **ProseMirror to Markdown conversion** for notes

## Installation

From GitLab (using uv):

```toml
# pyproject.toml
[project]
dependencies = ["apollo-client"]

[tool.uv.sources]
apollo-client = { git = "git@gitlab.qodev.ai:libs/apollo.git" }
```

Then run:
```bash
uv sync
```

## Quick Start

```python
from apollo import ApolloClient

async with ApolloClient() as client:
    # Search contacts
    contacts = await client.search_contacts(limit=10)
    for contact in contacts.items:
        print(f"{contact.name} - {contact.email}")

    # Get contact details
    contact = await client.get_contact("contact_id")
    print(f"Title: {contact.title} at {contact.company}")

    # Enrich organization data
    company = await client.enrich_organization("apollo.io")
    print(f"Employees: {company.get('estimated_num_employees')}")

    # Create a note
    await client.create_note(
        content="Great conversation about Q1 goals",
        contact_ids=["contact_id"],
    )
```

## Configuration

### API Key

Set environment variable:
```bash
export APOLLO_API_KEY="your_api_key"
```

Or pass directly:
```python
async with ApolloClient(api_key="your_api_key") as client:
    ...
```

### Timeout

Customize request timeout (default 30 seconds):
```python
async with ApolloClient(timeout=60.0) as client:
    ...
```

## Rate Limiting

Apollo.io enforces these limits:
- **400 requests/hour** (primary bottleneck for sustained operations)
- 200 requests/minute
- 2,000 requests/day

Monitor rate limits via `client.rate_limit_status`:

```python
async with ApolloClient() as client:
    await client.search_contacts(limit=10)

    status = client.rate_limit_status
    print(f"Hourly: {status['hourly_left']}/{status['hourly_limit']}")
    print(f"Minute: {status['minute_left']}/{status['minute_limit']}")
    print(f"Daily: {status['daily_left']}/{status['daily_limit']}")
```

**Best practices:**
- Add delays between requests (10+ seconds for sustained operations)
- Monitor `hourly_left` - stop if < 50 requests remaining
- Handle `RateLimitError` with exponential backoff

## Contact Matching

Three-tier fallback strategy for robust contact finding:

```python
contact_id = await client.find_contact_by_linkedin_url(
    linkedin_url="https://linkedin.com/in/johndoe",
    person_name="John Doe",  # Fallback if URL changed
    create_if_missing=True,  # Auto-create from People DB (210M+ contacts)
    contact_stage_id="stage_id",  # Stage to assign if created
)
```

**How it works:**
1. **LinkedIn URL search** - Exact match (most reliable)
2. **Name search** - Handles URL changes (requires unique match)
3. **People database** - Auto-create if enabled (verifies URL match)

**Common scenarios:**
- LinkedIn URLs change when users update custom URLs
- Name search returns multiple matches → skipped for safety
- People database doesn't support special characters (umlauts, etc.)

## API Methods

### Contacts

```python
# Search
contacts = await client.search_contacts(
    limit=100,
    q_keywords="CEO",
    contact_stage_ids=["stage_id"],
)

# Get by ID
contact = await client.get_contact("contact_id")

# Create
result = await client.create_contact(
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    title="CEO",
)

# Get contact stages
stages = await client.get_contact_stages()

# Find by LinkedIn URL (3-tier fallback)
contact_id = await client.find_contact_by_linkedin_url(
    linkedin_url="https://linkedin.com/in/johndoe",
    person_name="John Doe",
)
```

### Accounts

```python
# Search
accounts = await client.search_accounts(
    limit=100,
    q_organization_name="Apollo",
)

# Get by ID
account = await client.get_account("account_id")
```

### Deals / Opportunities

```python
# Search
deals = await client.search_deals(
    limit=100,
    opportunity_stage_ids=["stage_id"],
)

# Get by ID
deal = await client.get_deal("deal_id")
```

### Pipelines & Stages

```python
# List all pipelines
pipelines = await client.list_pipelines()

# Get pipeline by ID
pipeline = await client.get_pipeline("pipeline_id")

# List stages for pipeline
stages = await client.list_pipeline_stages("pipeline_id")
```

### Enrichment

```python
# Enrich organization (35M+ companies, free)
company = await client.enrich_organization("apollo.io")

# Enrich person (210M+ people, costs 1 credit)
person = await client.enrich_person("john@example.com")

# Search people database (free)
results = await client.search_people(q_keywords="CEO Apollo")
```

### Notes

```python
# Search notes
notes = await client.search_notes(
    contact_ids=["contact_id"],
    limit=50,
)

# Create note
result = await client.create_note(
    content="Meeting notes from Q1 planning",
    contact_ids=["contact_id"],
    account_ids=["account_id"],
)
```

### Activities

```python
# Search calls, tasks, emails
calls = await client.search_calls(limit=100)
tasks = await client.search_tasks(limit=100)
emails = await client.search_emails(limit=100)

# Create task
result = await client.create_task(
    contact_ids=["contact_id"],
    note="Follow up on proposal",
    priority="high",
)

# List contact activities
calls = await client.list_contact_calls("contact_id")
tasks = await client.list_contact_tasks("contact_id")
```

### News & Jobs

```python
# Get news for account
news = await client.list_account_news("account_id")

# Get job postings for account
jobs = await client.list_account_jobs("account_id")
```

## Models

All responses are typed Pydantic models:

- **Contact** - All contact fields (id, name, email, title, linkedin_url, phone_numbers, etc.)
- **Account** - All account fields (id, name, domain, employees, revenue, industries, tech stack, etc.)
- **Deal** - All deal fields (id, name, amount, stage, close_date, is_won, etc.)
- **Pipeline** - Pipeline info (id, title, is_default, sync_enabled, etc.)
- **Stage** - Stage info (id, name, probability, is_won, is_closed, etc.)
- **Note** - Notes with Markdown content (converted from ProseMirror JSON)
- **Call**, **Task**, **Email** - Activity records
- **EmploymentHistory** - Work history entries
- **PaginatedResponse[T]** - Generic pagination wrapper

## Error Handling

```python
from apollo import ApolloClient, AuthenticationError, RateLimitError, APIError

try:
    async with ApolloClient() as client:
        contacts = await client.search_contacts(limit=10)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after} seconds")
except APIError as e:
    print(f"API error: {e} (status: {e.status_code})")
```

## Development

```bash
# Install dependencies
make install

# Install pre-commit hooks
make install-hooks

# Run all checks (lint, format, typecheck, typos)
make check

# Run tests with coverage
make test

# Run tests without coverage
make test-fast

# Lint and format code
make lint
make format

# Type checking
make typecheck

# Spell check
make typos

# Clean generated files
make clean
```

## License

MIT
