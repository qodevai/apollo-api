# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
