"""Pydantic models for Apollo client.

Provides type-safe data structures for Apollo.io API responses.
All models use extra="allow" to capture any new/undocumented API fields.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, TypeAdapter


class ApolloModel(BaseModel):
    """Base model for all Apollo API objects. Captures undeclared fields via extras."""

    model_config = ConfigDict(extra="allow")


# ============================================================================
# SHARED VALUE TYPES
# ============================================================================


class PhoneEntry(ApolloModel):
    """Phone number entry (used in Account.primary_phone, Contact.phone_numbers)."""

    number: str | None = None
    source: str | None = None
    sanitized_number: str | None = None
    type: str | None = None


class Currency(ApolloModel):
    """Currency reference (used in Deal.currency)."""

    name: str | None = None
    iso_code: str | None = None
    symbol: str | None = None


class EmailParticipant(ApolloModel):
    """Email sender/recipient (used in Email.send_from, Email.recipients)."""

    email: str | None = None
    raw_name: str | None = None
    recipient_type_cd: str | None = None
    contact_id: str | None = None
    user_id: str | None = None


class ContactEmailEntry(ApolloModel):
    """Email entry in Contact.contact_emails list."""

    email: str | None = None
    email_md5: str | None = None
    email_sha256: str | None = None
    email_status: str | None = None
    email_true_status: str | None = None
    email_status_unavailable_reason: str | None = None
    extrapolated_email_confidence: float | None = None
    free_domain: bool | None = None
    position: int | None = None
    source: str | None = None
    third_party_vendor_name: str | None = None
    email_needs_tickling: bool | None = None


class ContactRole(ApolloModel):
    """Role entry in Contact.contact_roles list."""

    id: str | None = None
    name: str | None = None


class ContactRuleConfigStatus(ApolloModel):
    """Rule config status in Contact.contact_rule_config_statuses list."""

    id: str | None = None
    status: str | None = None


class ContactJobChangeEvent(ApolloModel):
    """Job change event data for a contact."""

    id: str | None = None
    person_id: str | None = None
    contact_id: str | None = None
    account_id: str | None = None
    contact_name: str | None = None
    title: str | None = None
    old_title: str | None = None
    old_organization_id: str | None = None
    new_organization_id: str | None = None
    new_organization_name: str | None = None
    new_organization_domain: str | None = None
    account_name: str | None = None
    is_processed: bool | None = None
    is_dismissed: bool | None = None
    charged: bool | None = None
    created_at: datetime | None = None


class AccountPlaybookStatus(ApolloModel):
    """Playbook status entry in Account.account_playbook_statuses list."""

    id: str | None = None
    status: str | None = None
    playbook_id: str | None = None


class AccountQueue(ApolloModel):
    """Queue entry in AccountDetail.account_queues list."""

    id: str | None = None
    name: str | None = None


class OpportunityRoleEntry(ApolloModel):
    """Role entry within OpportunityContactRole.role list."""

    opportunity_contact_role_type_id: str | None = None
    crm_role_id: str | None = None
    is_primary: bool | None = None
    crm_id: str | None = None


class EngagementTypeCount(ApolloModel):
    """Engagement type count entry in EngagementData.types_count."""

    type_cd: str | None = None
    count: int | None = None


class Technology(ApolloModel):
    """Technology stack entry (used in AccountDetail.current_technologies)."""

    uid: str | None = None
    name: str | None = None
    category: str | None = None


class OrganizationRef(ApolloModel):
    """Lightweight organization reference (used in AccountDetail.owned_by_organization, suborganizations)."""

    id: str
    name: str | None = None
    website_url: str | None = None


class ContactCampaignStatus(ApolloModel):
    """Campaign enrollment status for a contact."""

    id: str
    emailer_campaign_id: str | None = None
    send_email_from_user_id: str | None = None
    inactive_reason: str | None = None
    status: str | None = None
    added_at: datetime | None = None
    added_by_user_id: str | None = None
    finished_at: datetime | None = None
    paused_at: datetime | None = None
    auto_unpause_at: datetime | None = None
    send_email_from_email_address: str | None = None
    send_email_from_email_account_id: str | None = None
    manually_set_unpause: str | None = None
    failure_reason: str | None = None
    current_step_id: str | None = None


class OpportunityContactRole(ApolloModel):
    """Contact role within a deal/opportunity."""

    id: str
    contact_id: str | None = None
    is_primary: bool | None = None
    # API returns role as list of nested role objects, not plain strings
    role: list[OpportunityRoleEntry] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CrmNote(ApolloModel):
    """CRM-synced note reference."""

    id: str
    crm_id: str | None = None
    source_cd: str | None = None
    crm_deleted: bool | None = None
    crm_object_type_cd: str | None = None
    parent_crm_id: str | None = None
    last_sync: datetime | None = None
    key: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CrmJob(ApolloModel):
    """CRM sync job status."""

    id: str
    job_type: str | None = None
    status: str | None = None
    note: str | None = None
    retry_at: datetime | None = None
    created_at: datetime | None = None


class EngagementData(ApolloModel):
    """Engagement summary data."""

    types_count: list[EngagementTypeCount] = Field(default_factory=list)
    last_engagement_date: datetime | None = None


class EngagementGraphEntry(ApolloModel):
    """Monthly engagement activity counts for a contact or account."""

    year: int
    month: int
    inbound: int = 0
    outbound: int = 0


# ============================================================================
# CONTACT MODELS
# ============================================================================


class Contact(ApolloModel):
    """Contact model with all fields returned by Apollo API."""

    # Identity
    id: str
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    email: str | None = None
    title: str | None = None
    headline: str | None = None
    photo_url: str | None = None
    person_id: str | None = None

    # Company & Account
    organization_name: str | None = None
    organization_id: str | None = None
    account_id: str | None = None
    account: Account | None = None

    # Contact Management
    contact_stage_id: str | None = None
    owner_id: str | None = None
    creator_id: str | None = None
    label_ids: list[str] = Field(default_factory=list)
    source: str | None = None
    original_source: str | None = None
    source_display_name: str | None = None
    existence_level: str | None = None
    contact_roles: list[ContactRole] = Field(default_factory=list)
    typed_custom_fields: dict[str, Any] = Field(default_factory=dict)
    custom_field_errors: dict[str, Any] | list[Any] | None = None

    # Email
    email_status: str | None = None
    email_source: str | None = None
    email_true_status: str | None = None
    updated_email_true_status: bool | None = None
    email_from_customer: bool | None = None
    email_needs_tickling: bool | None = None
    email_unsubscribed: bool | None = None
    email_status_unavailable_reason: str | None = None
    email_domain_catchall: bool | None = None
    free_domain: bool | None = None
    contact_emails: list[ContactEmailEntry] = Field(default_factory=list)
    extrapolated_email_confidence: float | None = None
    has_pending_email_arcgate_request: bool | None = None
    has_email_arcgate_request: bool | None = None

    # Phone
    phone_numbers: list[PhoneEntry] = Field(default_factory=list)
    sanitized_phone: str | None = None
    direct_dial_status: str | None = None
    direct_dial_enrichment_failed_at: datetime | None = None
    account_phone_note: str | None = None

    # Social
    linkedin_url: str | None = None
    linkedin_uid: str | None = None
    facebook_url: str | None = None
    twitter_url: str | None = None

    # Location
    present_raw_address: str | None = None
    formatted_address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    street_address: str | None = None
    time_zone: str | None = None

    # Engagement & Intelligence
    is_likely_to_engage: bool | None = None
    intent_strength: str | None = None
    show_intent: bool | None = None
    emailer_campaign_ids: list[str] = Field(default_factory=list)
    contact_campaign_statuses: list[ContactCampaignStatus] = Field(default_factory=list)

    # Organization (nested, same shape as Account — all Account fields are optional)
    organization: Account | None = None

    # CRM Integration
    salesforce_id: str | None = None
    salesforce_lead_id: str | None = None
    salesforce_contact_id: str | None = None
    salesforce_account_id: str | None = None
    crm_owner_id: str | None = None
    crm_id: str | None = None
    crm_record_url: str | None = None
    hubspot_vid: str | None = None
    hubspot_company_id: str | None = None
    merged_crm_ids: list[str] | None = None
    queued_for_crm_push: bool | None = None

    # System
    contact_rule_config_statuses: list[ContactRuleConfigStatus] = Field(default_factory=list)
    suggested_from_rule_engine_config_id: str | None = None
    contact_job_change_event: ContactJobChangeEvent | None = None
    person_deleted: bool | None = None
    call_opted_out: bool | None = None

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_activity_date: datetime | None = None


class EmploymentHistory(ApolloModel):
    """Employment history entry for a contact."""

    id: str
    current: bool | None = None
    title: str | None = None
    organization_name: str | None = None
    organization_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    # Additional fields from API
    key: str | None = None
    kind: str | None = None
    description: str | None = None
    emails: list[str] | None = None
    degree: str | None = None
    major: str | None = None
    grade_level: str | None = None
    raw_address: str | None = None
    org_matched_by_name: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContactDetail(Contact):
    """Extended contact model with fields only returned by detail endpoint (GET /contacts/{id})."""

    # Detail-only fields
    employment_history: list[EmploymentHistory] = Field(default_factory=list)
    crm_job: CrmJob | None = None
    disable_flag: bool | None = None
    engagement_graph: list[EngagementGraphEntry] | None = None
    next_contact_id: str | None = None


# ============================================================================
# ACCOUNT MODELS
# ============================================================================


class Account(ApolloModel):
    """Account model with all fields returned by Apollo API."""

    # Identity
    id: str
    name: str | None = None
    domain: str | None = None
    primary_domain: str | None = None
    phone: str | None = None
    sanitized_phone: str | None = None
    phone_status: str | None = None
    primary_phone: PhoneEntry | None = None
    modality: str | None = None
    existence_level: str | None = None

    # Ownership & Management
    owner_id: str | None = None
    creator_id: str | None = None
    account_stage_id: str | None = None
    source: str | None = None
    original_source: str | None = None
    source_display_name: str | None = None
    label_ids: list[str] = Field(default_factory=list)
    typed_custom_fields: dict[str, Any] = Field(default_factory=dict)
    custom_field_errors: dict[str, Any] | list[Any] | None = None
    team_id: str | None = None
    parent_account_id: str | None = None

    # URLs & Social
    website_url: str | None = None
    blog_url: str | None = None
    logo_url: str | None = None
    linkedin_url: str | None = None
    linkedin_uid: str | None = None
    twitter_url: str | None = None
    facebook_url: str | None = None
    crunchbase_url: str | None = None
    angellist_url: str | None = None

    # Company details
    founded_year: int | None = None
    alexa_ranking: int | None = None
    publicly_traded_exchange: str | None = None
    publicly_traded_symbol: str | None = None
    languages: list[str] = Field(default_factory=list)
    sic_codes: list[str] = Field(default_factory=list)
    naics_codes: list[str] = Field(default_factory=list)

    # Location (account-level)
    raw_address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    street_address: str | None = None

    # Location (organization-level)
    organization_city: str | None = None
    organization_state: str | None = None
    organization_country: str | None = None
    organization_postal_code: str | None = None
    organization_street_address: str | None = None
    organization_raw_address: str | None = None
    suggest_location_enrichment: bool | None = None

    # Organization
    organization_id: str | None = None
    organization_headcount_six_month_growth: float | None = None
    organization_headcount_twelve_month_growth: float | None = None
    organization_headcount_twenty_four_month_growth: float | None = None

    # Contacts & Engagement
    num_contacts: int | None = None
    contact_emailer_campaign_ids: list[str] = Field(default_factory=list)
    contact_campaign_status_tally: dict[str, int] = Field(default_factory=dict)
    account_playbook_statuses: list[AccountPlaybookStatus] = Field(default_factory=list)
    intent_strength: str | None = None
    show_intent: bool | None = None
    suggested_from_rule_engine_config_id: str | None = None

    # CRM Integration
    crm_owner_id: str | None = None
    hubspot_id: str | None = None
    salesforce_id: str | None = None
    hubspot_record_url: str | None = None
    crm_record_url: str | None = None

    # Timestamps
    created_at: datetime | None = None
    last_activity_date: datetime | None = None


class AccountDetail(Account):
    """Extended account model with fields only returned by detail endpoint (GET /accounts/{id}).

    Includes enrichment data (industries, tech stack, revenue, org chart) not present in search.
    """

    # Enrichment — Industry & Description
    industries: list[str] = Field(default_factory=list)
    secondary_industries: list[str] = Field(default_factory=list)
    industry: str | None = None
    industry_tag_id: str | None = None
    industry_tag_hash: dict[str, str] = Field(default_factory=dict)
    keywords: list[str] = Field(default_factory=list)
    short_description: str | None = None

    # Enrichment — Size & Revenue
    estimated_num_employees: int | None = None
    annual_revenue: float | None = None
    annual_revenue_printed: str | None = None
    organization_revenue: float | None = None
    organization_revenue_printed: str | None = None
    retail_location_count: int | None = None

    # Enrichment — Technology Stack
    technology_names: list[str] = Field(default_factory=list)
    current_technologies: list[Technology] = Field(default_factory=list)

    # Enrichment — Org Chart
    org_chart_root_people_ids: list[str] = Field(default_factory=list)
    org_chart_sector: str | None = None
    org_chart_show_department_filter: bool | None = None
    org_chart_removed: bool | None = None
    num_suborganizations: int | None = None
    suborganizations: list[OrganizationRef] = Field(default_factory=list)
    owned_by_organization_id: str | None = None
    owned_by_organization: OrganizationRef | None = None

    # Detail-only metadata
    account_queues: list[AccountQueue] = Field(default_factory=list)
    disable_flag: bool | None = None
    engagement_graph: list[EngagementGraphEntry] | None = None
    snippets_loaded: bool | None = None


# ============================================================================
# DEAL MODELS
# ============================================================================


class Deal(ApolloModel):
    """Deal/Opportunity model with all fields returned by Apollo API."""

    # Identity
    id: str
    name: str | None = None
    amount: Decimal | None = None
    amount_in_team_currency: Decimal | None = None
    description: str | None = None
    existence_level: str | None = None
    source: str | None = None
    team_id: str | None = None

    # Pipeline & Stage
    opportunity_pipeline_id: str | None = None
    opportunity_stage_id: str | None = None
    stage_name: str | None = None
    stage_updated_at: datetime | None = None
    deal_probability: float | None = None
    probability: float | None = None

    # Forecast
    forecast_category: str | None = None
    forecasted_revenue: float | None = None
    manually_updated_forecast: str | None = None
    manually_updated_probability: float | None = None

    # Account & Owner
    account_id: str | None = None
    account: Account | None = None
    owner_id: str | None = None
    created_by_id: str | None = None

    # Close
    closed_date: str | None = None
    actual_close_date: str | None = None
    is_closed: bool | None = None
    is_won: bool | None = None
    closed_lost_reason: str | None = None
    closed_won_reason: str | None = None

    # Next Steps
    next_step: str | None = None
    next_step_date: str | None = None
    next_step_last_updated_at: datetime | None = None
    current_solutions: str | None = None
    deal_source: str | None = None

    # Currency
    currency: Currency | None = None
    exchange_rate_code: str | None = None
    exchange_rate_value: float | None = None

    # Related
    opportunity_contact_roles: list[OpportunityContactRole] = Field(default_factory=list)
    typed_custom_fields: dict[str, Any] = Field(default_factory=dict)
    num_contacts: int | None = None

    # CRM Integration
    crm_id: str | None = None
    crm_owner_id: str | None = None
    crm_record_url: str | None = None
    salesforce_id: str | None = None
    salesforce_owner_id: str | None = None

    # Timestamps
    created_at: datetime | None = None
    last_activity_date: datetime | None = None


# ============================================================================
# PIPELINE MODELS
# ============================================================================


class Pipeline(ApolloModel):
    """Pipeline model with all fields."""

    id: str
    title: str | None = None
    default_pipeline: bool | None = None
    display_order: int | None = None
    source: str | None = None
    external_id: str | None = None
    sync_enabled: bool | None = None
    team_id: str | None = None


class Stage(ApolloModel):
    """Pipeline stage model."""

    id: str
    name: str | None = None
    display_order: float | None = None
    probability: float | None = None
    type: str | None = None
    is_won: bool | None = None
    is_closed: bool | None = None
    description: str | None = None
    is_editable: bool | None = None
    opportunity_pipeline_id: str | None = None

    # Additional fields from API
    forecast_category_cd: str | None = None
    is_meeting_set: bool | None = None
    salesforce_id: str | None = None
    team_id: str | None = None


# ============================================================================
# ACTIVITY MODELS
# ============================================================================


class Note(ApolloModel):
    """Note model with Markdown-converted content.

    Note: title and content are synthesized by ApolloClient.search_notes() from
    the ProseMirror JSON. They will be None if constructed directly from raw API data.
    """

    id: str
    title: str | None = None
    content: str | None = None
    user_id: str | None = None

    # Associations (singular — API returns these too)
    contact_id: str | None = None
    account_id: str | None = None
    opportunity_id: str | None = None

    # Associations (plural)
    contact_ids: list[str] = Field(default_factory=list)
    account_ids: list[str] = Field(default_factory=list)
    opportunity_ids: list[str] = Field(default_factory=list)
    calendar_event_ids: list[str] = Field(default_factory=list)
    conversation_ids: list[str] = Field(default_factory=list)

    # Metadata
    pinned_to_top: bool | None = None
    is_org_chart_note: bool | None = None
    system: str | None = None
    conversation_id: str | None = None
    crm_notes: list[CrmNote] = Field(default_factory=list)

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Call(ApolloModel):
    """Phone call activity model."""

    id: str

    # Associations
    contact_id: str | None = None
    account_id: str | None = None
    user_id: str | None = None
    opportunity_id: str | None = None
    contact: Contact | None = None
    account: Account | None = None

    # Call details
    caller_name: str | None = None
    to_number: str | None = None
    from_number: str | None = None
    status: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration: int | None = None
    note: str | None = None
    note_text: str | None = None
    inbound: bool | None = None

    # Campaign
    emailer_campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_position: int | None = None
    outreach_task_id: str | None = None

    # Recording & Transcription
    recording_url: str | None = None
    transcribed: bool | None = None
    transcribing: bool | None = None
    transcription_progress: int | None = None
    transcription_too_long: bool | None = None
    voicemail_dropped: bool | None = None
    need_recording_upload: bool | None = None
    voice_setting_id: str | None = None

    # Telephony
    twilio_call_sid: str | None = None
    twilio_recording_sid: str | None = None
    agent_call_sid: str | None = None
    call_identifier: str | None = None
    conference_id: str | None = None
    from_country: str | None = None
    to_country: str | None = None
    from_email_open_trigger: bool | None = None
    parallel_dial_item_id: str | None = None

    # Classification
    phone_call_outcome_id: str | None = None
    phone_call_purpose_id: str | None = None
    conversation_id: str | None = None
    logged: bool | None = None
    credits: float | None = None

    # CRM Integration
    hubspot_id: str | None = None
    salesforce_id: str | None = None

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SortOrder(StrEnum):
    """Sort direction for search queries."""

    ASC = "asc"
    DESC = "desc"


class TaskPriority(StrEnum):
    """Task priority levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(StrEnum):
    """Task status values."""

    SCHEDULED = "scheduled"
    COMPLETE = "complete"
    OVERDUE = "overdue"


class TaskType(StrEnum):
    """Task type codes used by the Apollo API."""

    CALL = "call"
    ACCOUNT_CALL = "account_call"
    CONTACT_CALL = "contact_call"
    OUTREACH_MANUAL_EMAIL = "outreach_manual_email"
    LINKEDIN_STEP_CONNECT = "linkedin_step_connect"
    LINKEDIN_STEP_MESSAGE = "linkedin_step_message"
    LINKEDIN_STEP_INTERACT = "linkedin_step_interact_post"
    LINKEDIN_STEP_VIEW_PROFILE = "linkedin_step_view_profile"
    LINKEDIN_ACTIONS = "linkedin_actions"
    CONTACT_ACTION_ITEM = "contact_action_item"
    ACCOUNT_ACTION_ITEM = "account_action_item"


class LinkedInTemplate(ApolloModel):
    """LinkedIn message template embedded in campaign-based connect tasks."""

    id: str
    body_text: str | None = None


class OutreachTaskMessage(ApolloModel):
    """Standalone outreach message for LinkedIn tasks."""

    id: str | None = None
    body_text: str | None = None
    subject: str | None = None


class Task(ApolloModel):
    """Base task activity model with fields common to all task types."""

    id: str

    # Associations
    contact_id: str | None = None
    account_id: str | None = None
    user_id: str | None = None
    organization_id: str | None = None
    person_id: str | None = None
    contact: Contact | None = None
    account: Account | None = None

    # Task details
    title: str | None = None
    subject: str | None = None
    type: str | None = None
    priority: str | None = None
    status: str | None = None
    due_at: datetime | None = None
    note: str | None = None
    answered: bool | None = None

    # Automation
    linkedin_emailer_template: LinkedInTemplate | None = None
    playbook_id: str | None = None
    playbook_step_ids: list[str] = Field(default_factory=list)
    needs_playbook_autoprospecting: bool | None = None
    persona_ids: list[str] = Field(default_factory=list)
    rule_config_id: str | None = None
    recommendation_reasons: list[str] = Field(default_factory=list)
    recommended: bool | None = None

    # Ownership
    creator_id: str | None = None
    created_from: str | None = None
    completed_at: datetime | None = None
    completed_by_user_id: str | None = None
    skipped_at: datetime | None = None
    starred_by_user_ids: list[str] = Field(default_factory=list)

    # CRM Integration
    hubspot_id: str | None = None
    salesforce_id: str | None = None
    salesforce_type: str | None = None

    # Timestamps
    created_at: datetime | None = None


class EmailTask(Task):
    """Email task (outreach_manual_email) with emailer_message companion."""

    emailer_message: EmailerMessage | None = None
    engagement_data: EngagementData | None = None


class LinkedInConnectTask(Task):
    """LinkedIn connection request task (linkedin_step_connect)."""

    emailer_campaign_id: str | None = None
    linkedin_emailer_template: LinkedInTemplate | None = None
    standalone_outreach_task_message: OutreachTaskMessage | None = None
    campaign_name: str | None = None
    campaign_position: int | None = None


class LinkedInMessageTask(Task):
    """LinkedIn message task (linkedin_step_message) for existing connections."""

    opportunity_id: str | None = None
    standalone_outreach_task_message: OutreachTaskMessage | None = None
    engagement_data: EngagementData | None = None


# ---------------------------------------------------------------------------
# Discriminated union for polymorphic task deserialization
# ---------------------------------------------------------------------------

def _task_discriminator(v: Any) -> str:
    raw_type = v.get("type") if isinstance(v, dict) else getattr(v, "type", None)
    return {
        "outreach_manual_email": "email",
        "linkedin_step_connect": "linkedin_connect",
        "linkedin_step_message": "linkedin_message",
    }.get(raw_type, "base")


AnyTask = Annotated[
    Annotated[EmailTask, Tag("email")]
    | Annotated[LinkedInConnectTask, Tag("linkedin_connect")]
    | Annotated[LinkedInMessageTask, Tag("linkedin_message")]
    | Annotated[Task, Tag("base")],
    Discriminator(_task_discriminator),
]

_task_adapter: TypeAdapter[AnyTask] = TypeAdapter(AnyTask)


def resolve_task(data: dict[str, Any]) -> Task:
    """Validate a raw task dict into the most specific Task subclass."""
    return _task_adapter.validate_python(data)


class Email(ApolloModel):
    """Outreach email activity model."""

    id: str

    # Associations
    contact_id: str | None = None
    account_id: str | None = None
    user_id: str | None = None
    conversation_id: str | None = None

    # Email details
    subject: str | None = None
    body_text: str | None = None
    status: str | None = None
    type: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    to_email: str | None = None
    to_name: str | None = None
    cc_emails: list[str] = Field(default_factory=list)
    bcc_emails: list[str] = Field(default_factory=list)
    recipients: list[EmailParticipant] = Field(default_factory=list)
    attachment_ids: list[str] = Field(default_factory=list)

    # Campaign & Sequence
    emailer_campaign_id: str | None = None
    emailer_step_id: str | None = None
    emailer_touch_id: str | None = None
    campaign_name: str | None = None
    campaign_position: int | None = None
    email_account_id: str | None = None
    send_from: EmailParticipant | None = None
    send_from_info: str | None = None

    # Tracking
    enable_tracking: bool | None = None
    open_tracking_enabled: bool | None = None
    click_tracking_enabled: bool | None = None
    tracking_disabled_reason: str | None = None

    # Reply & Engagement
    replied: bool | None = None
    reply_class: str | None = None
    demoed: bool | None = None
    bounce: str | bool | None = None
    spam_blocked: bool | None = None
    personalized_opener: str | None = None

    # Sending
    async_sending: bool | None = None
    sensitive_info_redacted: bool | None = None
    show_unhealthy_domain_limit_warning: bool | None = None
    needs_dynamic_assemble: bool | None = None
    time_zone: str | None = None

    # Scheduling
    due_at: datetime | None = None
    due_at_source: str | None = None
    due_at_manually_changed: bool | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    not_sent_reason: str | None = None
    schedule_delayed_reason: str | None = None
    schedule_delayed_reason_details: str | None = None
    schedule_delayed_limit_reason: str | None = None
    campaign_max_emails_per_day: int | None = None
    step_max_emails_per_day: int | None = None

    # Provider
    provider_message_id: str | None = None
    provider_thread_id: str | None = None

    # CRM Integration
    crm_id: str | None = None

    # Timestamps
    created_at: datetime | None = None
    sent_at: datetime | None = None
    updated_at: datetime | None = None


class EmailerMessage(Email):
    """Embedded email message within a Task (may lack id when in draft state)."""

    id: str | None = None


# ============================================================================
# ADDITIONAL MODELS
# ============================================================================


class CalendarEventParticipant(ApolloModel):
    """Participant entry in CalendarEvent.participants list."""

    id: str
    contact_id: str | None = None
    email: str | None = None
    name: str | None = None
    domain: str | None = None
    response_status_cd: str | None = None
    booked_by: str | bool | None = None
    attended_conversation: str | bool | None = None
    auto_extracted: str | bool | None = None
    is_additional_guest: bool | None = None
    user_id: str | None = None
    time_zone: str | None = None


class CalendarEvent(ApolloModel):
    """Calendar event model with participant list."""

    id: str
    user_id: str | None = None
    title: str | None = None
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    salesforce_id: str | None = None
    contact_id: str | None = None
    participants: list[CalendarEventParticipant] = Field(default_factory=list)
    external_id: str | None = None
    participants_str: str | None = None


class ConversationParticipant(ApolloModel):
    """Participant in a recorded conversation."""

    id: str
    name: str | None = None
    contact_id: str | None = None
    user_id: str | None = None
    email: str | None = None
    is_internal_participant: bool | None = None
    account_name: str | None = None
    title: str | None = None


class TranscriptSegment(ApolloModel):
    """Single spoken segment within a conversation transcript."""

    id: str | None = None
    start_time: float | None = None  # seconds within recording
    end_time: float | None = None
    spoken_sentence: str | None = None
    participant_id: str | None = None
    participant_name: str | None = None


class VideoRecording(ApolloModel):
    """Video recording metadata for a conversation."""

    type_cd: str | None = None
    url: str | None = None
    state_cd: str | None = None


class CallSummaryNextStep(ApolloModel):
    """A next step from an AI-generated call summary."""

    id: str | None = None
    step: str | None = None
    due_at: str | None = None
    action_type: str | None = None
    task_id: str | None = None
    participant_id: str | None = None
    participant_name: str | None = None
    organization_name: str | None = None


class CallSummaryPoint(ApolloModel):
    """A pain point or objection from an AI-generated call summary."""

    id: str | None = None
    text: str | None = None
    participant_id: str | None = None
    participant_name: str | None = None
    organization_name: str | None = None


class CallSummary(ApolloModel):
    """AI-generated summary of a conversation."""

    outcome: str | None = None
    pricing_discussion: str | None = None
    next_steps: list[CallSummaryNextStep] | None = None
    pain_points: list[CallSummaryPoint] | None = None
    objections: list[CallSummaryPoint] | None = None


class ConversationDeal(ApolloModel):
    """Deal associated with a conversation."""

    id: str
    name: str | None = None
    account_name: str | None = None
    opportunity_stage_id: str | None = None


class Conversation(ApolloModel):
    """Conversation from search endpoint."""

    id: str
    start_time: datetime | None = None
    duration: int | None = None
    host: str | None = None
    host_id: str | None = None
    state: str | None = None
    failure_code: str | None = None
    bot_call_ended_reason: str | None = None
    conversation_type: str | None = None
    topic: str | None = None
    comment_count: int | None = None
    is_internal: bool | None = None
    is_private: bool | None = None
    can_access_conversation: bool | None = None
    thumbnail_url: str | None = None
    team_id: str | None = None
    participant_names: list[str] = Field(default_factory=list)
    account_names: list[str] = Field(default_factory=list)
    account_ids: list[str] = Field(default_factory=list)
    participants_info: list[ConversationParticipant] = Field(default_factory=list)
    deals: list[ConversationDeal] = Field(default_factory=list)


class ConversationDetail(Conversation):
    """Extended conversation from detail endpoint — adds transcript, summary, recording."""

    transcript: list[TranscriptSegment] = Field(default_factory=list)
    video_recording: VideoRecording | None = None
    call_summary: CallSummary | None = None
    editable_call_summary: CallSummary | None = None
    key_topics: dict[str, Any] = Field(default_factory=dict)
    pushed_to_crm: bool | None = None
    is_shared_conversation: bool | None = None
    is_clip: bool | None = None
    opportunity_ids: list[str] = Field(default_factory=list)


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
