"""Pydantic models for Apollo client.

Provides type-safe data structures for Apollo.io API responses.
"""

from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

# ============================================================================
# CONTACT MODELS
# ============================================================================


class Contact(BaseModel):
    """Contact model with all fields returned by Apollo API."""

    id: str
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    title: str | None = None
    company: str | None = None
    company_domain: str | None = None
    account_id: str | None = None
    stage: str | None = None
    owner: str | None = None
    location: str | None = None
    phone_numbers: list[dict] = Field(default_factory=list)
    linkedin_url: str | None = None
    label_ids: list[str] = Field(default_factory=list)
    last_activity: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class EmploymentHistory(BaseModel):
    """Employment history entry for a contact."""

    id: str
    current: bool = False
    title: str | None = None
    organization_name: str | None = None
    organization_id: str | None = None
    start_date: str | None = None  # YYYY-MM-DD format
    end_date: str | None = None  # YYYY-MM-DD format (null if current)


# ============================================================================
# ACCOUNT MODELS
# ============================================================================


class Account(BaseModel):
    """Account model with all fields returned by Apollo API."""

    # Core fields
    id: str
    name: str | None = None
    domain: str | None = None
    stage: str | None = None
    owner: str | None = None
    phone: str | None = None
    location: str | None = None
    description: str | None = None
    organization_data: dict | None = None
    created_at: str | None = None
    last_activity: str | None = None

    # URLs & Social
    website_url: str | None = None
    logo_url: str | None = None
    linkedin_url: str | None = None
    twitter_url: str | None = None
    facebook_url: str | None = None
    crunchbase_url: str | None = None
    angellist_url: str | None = None

    # Company details
    industries: list[str] = Field(default_factory=list)
    secondary_industries: list[str] = Field(default_factory=list)
    sic_codes: list[str] = Field(default_factory=list)
    naics_codes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    # Size & Financials
    employees: int | None = None
    estimated_num_employees: int | None = None
    founded_year: int | None = None
    revenue: str | None = None
    organization_revenue: float | None = None
    organization_revenue_printed: str | None = None

    # Funding
    total_funding: float | None = None
    total_funding_printed: str | None = None
    latest_funding_round_date: str | None = None
    latest_funding_stage: str | None = None
    funding_events: list[dict] = Field(default_factory=list)

    # Structured location
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    street_address: str | None = None

    # Technology Stack
    technology_names: list[str] = Field(default_factory=list)
    current_technologies: list[dict] = Field(default_factory=list)

    # CRM Metadata
    owner_id: str | None = None
    account_stage_id: str | None = None
    num_contacts: int | None = None

    # External IDs
    organization_id: str | None = None
    hubspot_id: str | None = None
    salesforce_id: str | None = None
    hubspot_record_url: str | None = None
    crm_record_url: str | None = None


# ============================================================================
# DEAL MODELS
# ============================================================================


class Deal(BaseModel):
    """Deal/Opportunity model with all fields returned by Apollo API."""

    id: str
    name: str | None = None
    amount: Decimal | None = None
    stage: str | None = None
    account_id: str | None = None
    account_name: str | None = None
    owner: str | None = None
    account: dict | None = None
    close_date: str | None = None
    is_closed: bool | None = None
    is_won: bool | None = None
    created_at: str | None = None


# ============================================================================
# PIPELINE MODELS
# ============================================================================


class Pipeline(BaseModel):
    """Pipeline model with all fields."""

    id: str
    title: str | None = None
    is_default: bool | None = None
    source: str | None = None
    external_id: str | None = None
    sync_enabled: bool | None = None
    team_id: str | None = None


class Stage(BaseModel):
    """Pipeline stage model."""

    id: str
    name: str | None = None
    display_order: int | None = None
    probability: int | None = None
    type: str | None = None
    is_won: bool | None = None
    is_closed: bool | None = None
    description: str | None = None
    is_editable: bool | None = None


# ============================================================================
# ACTIVITY MODELS
# ============================================================================


class Note(BaseModel):
    """Note model with Markdown-converted content."""

    id: str
    title: str
    content: str  # Converted from ProseMirror JSON to Markdown
    created_at: str | None = None
    updated_at: str | None = None
    user_id: str | None = None
    contact_ids: list[str] = Field(default_factory=list)
    account_ids: list[str] = Field(default_factory=list)
    opportunity_ids: list[str] = Field(default_factory=list)
    pinned_to_top: bool = False


class Call(BaseModel):
    """Phone call activity model."""

    id: str
    contact_id: str | None = None
    account_id: str | None = None
    user_id: str | None = None  # Caller
    user_name: str | None = None
    contact_name: str | None = None
    account_name: str | None = None
    to_number: str | None = None
    from_number: str | None = None
    status: str | None = None  # queued, ringing, in-progress, completed, no_answer, failed, busy
    start_time: str | None = None
    end_time: str | None = None
    duration: int | None = None  # seconds
    note: str | None = None
    inbound: bool | None = None
    created_at: str | None = None


class Task(BaseModel):
    """Task activity model."""

    id: str
    contact_ids: list[str] = Field(default_factory=list)
    user_id: str | None = None  # Task owner
    user_name: str | None = None
    type: str | None = None  # call, outreach_manual_email, linkedin_step_*, action_item
    priority: str | None = None  # high, medium, low
    status: str | None = None  # scheduled, completed, archived
    due_at: str | None = None
    note: str | None = None
    created_at: str | None = None


class Email(BaseModel):
    """Outreach email activity model."""

    id: str
    contact_id: str | None = None
    contact_name: str | None = None
    user_id: str | None = None  # Sender
    user_name: str | None = None
    campaign_id: str | None = None  # Sequence/campaign
    campaign_name: str | None = None
    subject: str | None = None
    status: str | None = None  # delivered, opened, clicked, bounced, drafted, etc.
    sent_at: str | None = None
    opened_at: str | None = None
    clicked_at: str | None = None
    reply_sentiment: str | None = None  # willing_to_meet, not_interested, out_of_office, etc.
    created_at: str | None = None


# ============================================================================
# ADDITIONAL MODELS
# ============================================================================


class NewsArticle(BaseModel):
    """News article model."""

    title: str | None = None
    url: str | None = None
    published_at: str | None = None
    category: str | None = None
    summary: str | None = None


class JobPosting(BaseModel):
    """Job posting model."""

    title: str | None = None
    location: str | None = None
    department: str | None = None
    url: str | None = None
    posted_at: str | None = None


# ============================================================================
# GENERIC PAGINATED RESPONSE
# ============================================================================

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response with items, total count, and page number."""

    items: list[T]
    total: int
    page: int = 1
