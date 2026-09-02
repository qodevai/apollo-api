# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0] - 2026-09-02

### Added

- **`update_opportunity(opportunity_id, **fields)`** — `PATCH /opportunities/{id}`, live-verified against the real API. Common fields: `name`, `amount`, `opportunity_stage_id`, `closed_date`, `account_id`, `owner_id`, `next_step`, `next_step_date`, `description`. Distinct from `create_deal`'s `POST /opportunities`. Raises `ValueError` if no fields are given.
- **`get_note(note_id)`** — `GET /notes/{id}`, returns a `Note` with ProseMirror content converted to Markdown (same conversion as `search_notes()`). The response-wrapping key was not live-verifiable during development (`/notes/search`'s own daily quota was exhausted — see [CLAUDE.md](CLAUDE.md#5-api-quirks)); it follows the `{"note": {...}}` convention every other `get_*` method uses and falls back to the raw body if that key is absent.
- `RoleAssignmentError` (new exception, exported from the package root) — raised by `update_opportunity_roles` when a requested role isn't present on a post-write read-back. Carries `.opportunity_id` and `.missing_contact_ids`.

### Fixed

- **`update_opportunity_roles` now fails loud instead of silently returning a role that was never persisted.** Live-observed: a set-role call returned Apollo's 200 + deal JSON with no error while the role was **not** actually saved (a read-back minutes later showed 0 roles); the identical call succeeded on retry. The write response can no longer be trusted on its own — the method now always re-reads the opportunity after writing and raises `RoleAssignmentError` if any requested `contact_id` is missing from the fresh read-back, instead of returning the (possibly stale/wrong) write response.

## [0.6.0] - 2026-08-31

### Added

- **`create_task` takes `user_id`, `due_at` and `title` directly.** Apollo rejects
  task creation with `{"error": "Invalid user or creator id"}` unless an owner is
  supplied, and the only way to set a due date was to know that `**fields` was
  forwarded verbatim. Both are now named parameters, documented, and `due_at`
  accepts a `datetime` (ISO-serialised for you) as well as a preformatted string.
  Unset optionals stay out of the payload. `note` is optional too and is omitted
  rather than sent as an empty string; Apollo accepts a task without it (verified
  against the live API). A **naive `due_at` is rejected** with a `ValueError` —
  it would serialise without an offset and leave the intended instant ambiguous.

- **`create_linkedin_connect_request(contact_id, note=None, ...)`** — a LinkedIn
  connection request that defaults to carrying no message. On a
  `linkedin_step_connect` task the note travels with the invitation, so `note`
  defaults to `None` and the docstring says plainly that whatever you pass is seen
  by the recipient; internal context goes in `title`, which stays inside Apollo.
  `create_linkedin_connect_task` remains for Apollo's structured outreach message
  payload.

### Changed

- **`RateLimitError` now reports what Apollo actually said.** The message was the
  constant `"Rate limit exceeded. Apollo limits: 400/hour, 200/min, 2000/day"` —
  identical whether the minute, the hour or the day was spent, and on which
  endpoint. Apollo meters **per endpoint**, so that ambiguity actively misled:
  in one incident `/notes` was at `daily 0/2000` while `/tasks` on the same key
  reported `1984/2000` left, and the message gave no way to tell.

  It now names the endpoint and the exhausted window, e.g.
  `Rate limit exceeded on /notes: daily 0/2000 exhausted (buckets: minute
  200/200, hourly 400/400, daily 0/2000). Apollo meters per endpoint, so other
  endpoints may still have budget.` The exception carries `.endpoint` and
  `.limits` so a caller can pace itself instead of guessing.

- **`rate_limit_status` distinguishes an absent header from a spent bucket.**
  Values are now `int | None`; previously `int(header or 0)` reported a missing
  header as `0`, i.e. as exhaustion that was never observed. **Breaking** for
  callers annotating the return as `dict[str, int]`.

## [0.5.0] - 2026-07-10

### Fixed

- **People search** now uses `/mixed_people/api_search`; the old `/mixed_people/search` is deprecated for API callers (422). Note the new endpoint returns teaser data only (no full name/email/linkedin_url without a credit-consuming reveal). The `find_contact_by_linkedin_url` auto-creation step is retired accordingly (it warns; `create_if_missing` is a documented no-op).
- **Deal name search** uses `q_opportunity_name`, not `q_keywords` (which Apollo silently ignores on `/opportunities/search`). `DEAL_SEARCH_FILTERS` allows `q_opportunity_name` and rejects `q_keywords`.
- `list_contact_tasks` now filters the tasks search by `contact_ids` (the `/contacts/{id}/tasks` route was removed by Apollo — 404).
- `list_account_jobs` resolves the account's `organization_id` and reads `/organizations/{org_id}/job_postings` (the `/accounts/{id}/job_postings` route was removed).

### Added

- Search-filter validation across **all** `search_*` methods: unknown filter keys raise (documented endpoints: contacts/deals/people/accounts) or warn (undocumented activity endpoints), preventing Apollo's silent-drop → unfiltered-default-page footgun.
- `search_*` docstrings now document each filter's empirically-verified accepted format (seniority enums, `"min,max"` employee ranges, location formats, dict ranges, email-status values, canonical `linkedin_url`).

### Removed

- **Breaking:** `list_contact_calls` and `list_account_news` — Apollo removed the underlying routes (`/contacts/{id}/calls`, `/accounts/{id}/news`) with no working replacement.

## [0.4.0] - 2026-07-09

### Added

- `create_deal(name, **fields)` creates a deal/opportunity via `POST /opportunities`. `name` is the only required field; optional `owner_id`, `account_id`, `amount`, `opportunity_stage_id`, `closed_date` are forwarded as-is. Requires a **master** API key (non-master keys return 403). Live-verified against the real API.

### Fixed

- `update_opportunity_roles(...)` now sends Apollo's expected **nested** role shape — `{"contact_id": …, "is_primary": …, "role": [{"opportunity_contact_role_type_id": …, "is_primary": …}]}` — instead of the flat `opportunity_contact_role_type_id` on the entry. The flat shape made Apollo 422 with `undefined method 'map' for nil`, so setting a contact's role on a deal failed every time. The public `RoleAssignment` interface is unchanged (callers still pass flat entries).
- `search_accounts(**filters)` now validates filter keys against an allowlist (`q_organization_name`, `account_stage_ids`, `account_label_ids`, `sort_by_field`, `sort_ascending`) and raises `ValueError` on unknown keys. Apollo silently ignores unrecognised keys and returns an unfiltered default page that looks like a real match (e.g. `query="…"` returned ~28k accounts, "Google" first) — fail-loud now prevents wrong-account attribution.

## [0.3.2] - 2026-07-08

### Fixed

- `search_tasks()` could raise `AttributeError` while *handling* an unparseable row: the skip path called `raw.get("id")` assuming `raw` was a dict, so a non-dict row (e.g. a stray `null`) turned the intended "skip one bad row" into a whole-page crash. The id lookup is now guarded (`isinstance(raw, dict)`), and iteration tolerates a null `tasks` value (`result.get("tasks") or []`).

## [0.3.1] - 2026-07-08

### Changed

- `update_opportunity_roles(...)` now types its `roles` parameter as `list[RoleAssignment]` (a `TypedDict` with a required `contact_id` and optional `opportunity_contact_role_type_id` / `is_primary`) instead of the loose `list[dict]`, giving callers type checking and autocomplete. `RoleAssignment` is exported from the package root. Non-breaking — plain dicts still satisfy it structurally.

## [0.3.0] - 2026-07-08

### Added

- `ApolloClient.update_opportunity_roles(opportunity_id, roles)` — `POST /opportunities/update_roles`. Sets the contact roles on a deal (replaces the full set; read the current roles from `get_deal(...).opportunity_contact_roles` and modify). Returns the updated `Deal`. Surfaces the previously curl-only role-management endpoint.
- `ApolloClient.list_custom_fields()` — `GET /typed_custom_fields`. Returns the account/contact/opportunity custom field definitions as a new `CustomField` model (`id`, `modality`, `name`, `type`, `picklist_options`, `mapped_crm_field`).
- `CustomField` model, exported from the package root.

## [0.2.1] - 2026-07-01

### Fixed
- `normalize_linkedin_url()` normalized to `https://` and never added `www`, but Apollo stores and **exact-matches** LinkedIn URLs as `http://www.linkedin.com/in/<slug>`. As a result `find_contact_by_linkedin_url()`'s URL tier always missed (silently falling through to name search), and any `search_contacts(linkedin_url=...)` filter built from it returned zero. It now produces Apollo's `http://www` form, so URL lookups actually match.

## [0.2.0] - 2026-06-02

### Fixed
- `create_note()` posted `{"note": <plaintext>}`, which Apollo silently ignores — notes were created with empty content. It now serialises `content` to ProseMirror JSON and posts it in the `content` field (the format Apollo stores and `search_notes()` reads back). Closes #6.

### Added
- `markdown_to_prosemirror()` in `utils` — inverse of `prosemirror_to_markdown()` (title, paragraphs, bullet/ordered lists).
- `create_note(..., title=...)` — optional note title (rendered as the ProseMirror `noteTitle`).
- `ApolloClient.delete_note(note_id)` — `DELETE /notes/{id}`.

### Changed
- `create_note()` association args (`contact_ids`, `account_ids`, `opportunity_ids`) are now keyword-only, so the new positional `title` can't be confused with them.

## [0.1.3] - 2026-02-23

### Added
- `ActionItemTask` subclass for `action_item` task type
- `OtherTask` fallback subclass — `resolve_task()` now returns `OtherTask` for unknown task types instead of raising `ValidationError`
- `OpportunityContactRoleType` model for role type definitions (Decision Maker, Buyer, etc.)
- `ApolloClient.list_opportunity_contact_role_types()` — lookup endpoint for role type ID → name mapping (undocumented `POST /opportunity_contact_role_types/search`)

### Fixed
- `Deal.closed_date`, `Deal.actual_close_date`, `Deal.next_step_date` now parsed as `datetime` (were `str`)
- `EmploymentHistory.start_date`, `EmploymentHistory.end_date` now parsed as `date` (were `str`)
- `CallSummaryNextStep.due_at` now parsed as `datetime` (was `str`)
- `NewsArticle.published_at`, `JobPosting.posted_at` now parsed as `datetime` (were `str`)
- `search_conversations()` default and max limit corrected from 100 to 25 (Apollo API caps at 25)

## [0.1.2] - 2026-02-23

### Added
- **11 typed Task subclasses** with native Pydantic `Discriminator("type")` — CallTask, AccountCallTask, ContactCallTask, LinkedInInteractTask, LinkedInViewProfileTask, LinkedInActionsTask, ContactActionItemTask, AccountActionItemTask (plus existing EmailTask, LinkedInConnectTask, LinkedInMessageTask)
- `resolve_task()` function for polymorphic task deserialization (raises `ValidationError` on unknown/missing types)
- `Task` type alias — union of all task subclasses
- `BaseTask` base class — common fields shared by all task types (renamed from `Task`)

## [0.1.1] - 2026-02-20

### Added
- Comprehensive client.py test suite — 55 new tests covering all public methods, error handling, and the 3-tier LinkedIn contact matching strategy (client.py coverage: 33% → 98%)
- CHANGELOG.md following Keep a Changelog format
- GitHub release for v0.1.0

## [0.1.0] - 2026-02-20

Initial public release on PyPI (previously internal at qodev).

### Added
- **Async API client** with context manager support and httpx
- **40+ API methods** across contacts, accounts, deals, pipelines, notes, calls, tasks, emails, calendar events, conversations, enrichment, and usage
- **Full Pydantic v2 models** for all API responses with `extra="allow"` for forward compatibility
- **Task subclass hierarchy** — EmailTask, LinkedInConnectTask, LinkedInMessageTask with typed enums
- **3-tier contact matching** — LinkedIn URL → name fallback → People DB auto-creation
- **Built-in rate limit tracking** from response headers (400/hour, 200/min, 2000/day)
- **ProseMirror to Markdown conversion** for Apollo notes
- **Custom exceptions** — AuthenticationError, RateLimitError, APIError
- **py.typed marker** for downstream type checking
- **GitHub Actions CI** — lint (ruff), typecheck (pyright), test (pytest)
- **PyPI publishing** via Trusted Publishers (OIDC)
