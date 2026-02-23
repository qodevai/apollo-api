# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `ActionItemTask` subclass for `action_item` task type
- `OtherTask` fallback subclass — `resolve_task()` now returns `OtherTask` for unknown task types instead of raising `ValidationError`

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
