"""Tests for Apollo models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from qodev_apollo_api.models import (
    Account,
    AccountActionItemTask,
    AccountCallTask,
    AccountDetail,
    AccountPlaybookStatus,
    AccountQueue,
    ActionItemTask,
    ApolloModel,
    BaseTask,
    Call,
    CallSummary,
    CallSummaryNextStep,
    CallSummaryPoint,
    CallTask,
    Contact,
    ContactActionItemTask,
    ContactCallTask,
    ContactCampaignStatus,
    ContactDetail,
    ContactEmailEntry,
    ContactJobChangeEvent,
    ContactRole,
    ContactRuleConfigStatus,
    Conversation,
    ConversationDeal,
    ConversationDetail,
    ConversationParticipant,
    CrmJob,
    CrmNote,
    Currency,
    Deal,
    Email,
    EmailerMessage,
    EmailParticipant,
    EmailTask,
    EmploymentHistory,
    EngagementData,
    EngagementGraphEntry,
    EngagementTypeCount,
    LinkedInActionsTask,
    LinkedInConnectTask,
    LinkedInInteractTask,
    LinkedInMessageTask,
    LinkedInViewProfileTask,
    Note,
    OpportunityContactRole,
    OpportunityContactRoleType,
    OpportunityRoleEntry,
    OrganizationRef,
    OtherTask,
    PaginatedResponse,
    PhoneEntry,
    Pipeline,
    Stage,
    TaskType,
    Technology,
    TranscriptSegment,
    VideoRecording,
    resolve_task,
)

# ============================================================================
# BASE MODEL
# ============================================================================


def test_apollo_model_extra_allow():
    """All Apollo models inherit extra='allow' from ApolloModel."""
    model = ApolloModel.model_validate({"unknown": "value"})
    assert model.model_extra == {"unknown": "value"}


# ============================================================================
# CONTACT
# ============================================================================


def test_contact_model():
    """Test Contact model validation."""
    contact = Contact(
        id="test_id",
        name="John Doe",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        title="CEO",
        organization_name="Example Corp",
    )
    assert contact.id == "test_id"
    assert contact.name == "John Doe"
    assert contact.email == "john@example.com"


def test_contact_model_optional_fields():
    """Test Contact model with minimal fields."""
    contact = Contact(id="test_id")
    assert contact.id == "test_id"
    assert contact.name is None
    assert contact.email is None


def test_contact_custom_field_errors_nullable():
    """Test custom_field_errors accepts None from API (field is null in embedded responses)."""
    contact = Contact.model_validate({"id": "c1", "custom_field_errors": None})
    assert contact.custom_field_errors is None


def test_contact_custom_field_errors_default():
    """Test custom_field_errors defaults to None when absent."""
    contact = Contact.model_validate({"id": "c1"})
    assert contact.custom_field_errors is None


def test_contact_extra_fields():
    """Test Contact model captures unknown API fields."""
    contact = Contact.model_validate({"id": "test_id", "some_new_field": "value"})
    assert contact.id == "test_id"
    assert contact.model_extra == {"some_new_field": "value"}


def test_contact_with_phone_entries():
    """Test Contact deserializes phone_numbers into PhoneEntry models."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "phone_numbers": [
                {"number": "+1234567890", "type": "mobile", "source": "apollo"},
            ],
        }
    )
    assert len(contact.phone_numbers) == 1
    assert isinstance(contact.phone_numbers[0], PhoneEntry)
    assert contact.phone_numbers[0].number == "+1234567890"
    assert contact.phone_numbers[0].type == "mobile"


def test_contact_with_campaign_statuses():
    """Test Contact deserializes contact_campaign_statuses into typed models."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "contact_campaign_statuses": [
                {
                    "id": "cs1",
                    "status": "active",
                    "emailer_campaign_id": "camp1",
                    "added_at": "2025-01-15T10:00:00.000+00:00",
                },
            ],
        }
    )
    assert len(contact.contact_campaign_statuses) == 1
    assert isinstance(contact.contact_campaign_statuses[0], ContactCampaignStatus)
    assert contact.contact_campaign_statuses[0].status == "active"
    assert isinstance(contact.contact_campaign_statuses[0].added_at, datetime)


def test_contact_with_embedded_account():
    """Test Contact deserializes embedded account into Account model."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "account": {"id": "a1", "name": "Acme Corp", "domain": "acme.com"},
        }
    )
    assert isinstance(contact.account, Account)
    assert contact.account.name == "Acme Corp"


def test_contact_with_contact_emails():
    """Test Contact deserializes contact_emails into ContactEmailEntry models."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "contact_emails": [
                {
                    "email": "test@example.com",
                    "email_status": "verified",
                    "position": 0,
                    "free_domain": False,
                    "source": "Apollo",
                },
            ],
        }
    )
    assert len(contact.contact_emails) == 1
    assert isinstance(contact.contact_emails[0], ContactEmailEntry)
    assert contact.contact_emails[0].email == "test@example.com"
    assert contact.contact_emails[0].email_status == "verified"
    assert contact.contact_emails[0].position == 0


def test_contact_with_contact_roles():
    """Test Contact deserializes contact_roles into ContactRole models."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "contact_roles": [{"id": "r1", "name": "Decision Maker"}],
        }
    )
    assert len(contact.contact_roles) == 1
    assert isinstance(contact.contact_roles[0], ContactRole)
    assert contact.contact_roles[0].name == "Decision Maker"


def test_contact_with_organization():
    """Test Contact deserializes organization into Account model."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "organization": {
                "id": "org1",
                "name": "Acme Corp",
                "website_url": "https://acme.com",
                "primary_domain": "acme.com",
                "founded_year": 2010,
            },
        }
    )
    assert isinstance(contact.organization, Account)
    assert contact.organization.name == "Acme Corp"
    assert contact.organization.founded_year == 2010


def test_contact_with_job_change_event():
    """Test Contact deserializes contact_job_change_event into ContactJobChangeEvent."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "contact_job_change_event": {
                "id": "jce1",
                "contact_id": "c1",
                "title": "VP Engineering",
                "old_title": "Senior Engineer",
                "new_organization_name": "New Corp",
                "is_processed": True,
                "is_dismissed": False,
            },
        }
    )
    assert isinstance(contact.contact_job_change_event, ContactJobChangeEvent)
    assert contact.contact_job_change_event.title == "VP Engineering"
    assert contact.contact_job_change_event.old_title == "Senior Engineer"
    assert contact.contact_job_change_event.is_processed is True


def test_contact_with_rule_config_statuses():
    """Test Contact deserializes contact_rule_config_statuses."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "contact_rule_config_statuses": [{"id": "rcs1", "status": "active"}],
        }
    )
    assert len(contact.contact_rule_config_statuses) == 1
    assert isinstance(contact.contact_rule_config_statuses[0], ContactRuleConfigStatus)


def test_contact_datetime_fields():
    """Test Contact parses timestamp strings into datetime objects."""
    contact = Contact.model_validate(
        {
            "id": "c1",
            "created_at": "2025-01-15T10:00:00.000+00:00",
            "updated_at": "2025-02-01T12:30:00.000Z",
        }
    )
    assert isinstance(contact.created_at, datetime)
    assert isinstance(contact.updated_at, datetime)


# ============================================================================
# CONTACT DETAIL
# ============================================================================


def test_contact_detail_subclass():
    """Test ContactDetail extends Contact with detail-only fields."""
    detail = ContactDetail.model_validate(
        {
            "id": "c_123",
            "name": "John Doe",
            "employment_history": [{"id": "eh_1", "_id": "eh_1", "title": "CTO"}],
            "disable_flag": False,
        }
    )
    assert isinstance(detail, Contact)
    assert detail.name == "John Doe"
    assert len(detail.employment_history) == 1
    assert isinstance(detail.employment_history[0], EmploymentHistory)
    assert detail.disable_flag is False


def test_contact_detail_with_crm_job():
    """Test ContactDetail deserializes crm_job into CrmJob model."""
    detail = ContactDetail.model_validate(
        {
            "id": "c1",
            "crm_job": {
                "id": "job1",
                "job_type": "push_contacts",
                "status": "failed",
                "note": "Missing email",
            },
        }
    )
    assert isinstance(detail.crm_job, CrmJob)
    assert detail.crm_job.status == "failed"


# ============================================================================
# EMPLOYMENT HISTORY
# ============================================================================


def test_employment_history_model():
    """Test EmploymentHistory model validation."""
    emp = EmploymentHistory(
        id="emp_123",
        current=True,
        title="CTO",
        organization_name="Acme Corp",
        start_date="2020-01-01",
    )
    assert emp.id == "emp_123"
    assert emp.current is True
    assert emp.title == "CTO"


def test_employment_history_current_defaults_to_none():
    """Test EmploymentHistory.current defaults to None (unknown), not False."""
    emp = EmploymentHistory(id="emp_123")
    assert emp.current is None


def test_employment_history_extra_fields():
    """Test EmploymentHistory captures unknown API fields."""
    emp = EmploymentHistory.model_validate({"id": "emp_123", "new_api_field": "data"})
    assert emp.model_extra == {"new_api_field": "data"}


# ============================================================================
# ACCOUNT
# ============================================================================


def test_account_model():
    """Test Account model validation."""
    account = Account(
        id="acc_123",
        name="Example Corp",
        domain="example.com",
        num_contacts=50,
    )
    assert account.id == "acc_123"
    assert account.name == "Example Corp"
    assert account.domain == "example.com"
    assert account.num_contacts == 50


def test_account_extra_fields():
    """Test Account model captures unknown API fields."""
    account = Account.model_validate({"id": "acc_123", "unknown_field": 42})
    assert account.model_extra == {"unknown_field": 42}


def test_account_with_primary_phone():
    """Test Account deserializes primary_phone into PhoneEntry model."""
    account = Account.model_validate(
        {
            "id": "a1",
            "primary_phone": {
                "number": "+1234567890",
                "source": "crm",
                "sanitized_number": "1234567890",
            },
        }
    )
    assert isinstance(account.primary_phone, PhoneEntry)
    assert account.primary_phone.number == "+1234567890"


def test_account_with_playbook_statuses():
    """Test Account deserializes account_playbook_statuses into typed models."""
    account = Account.model_validate(
        {
            "id": "a1",
            "account_playbook_statuses": [
                {"id": "ps1", "status": "active", "playbook_id": "pb1"},
            ],
        }
    )
    assert len(account.account_playbook_statuses) == 1
    assert isinstance(account.account_playbook_statuses[0], AccountPlaybookStatus)
    assert account.account_playbook_statuses[0].playbook_id == "pb1"


# ============================================================================
# ACCOUNT DETAIL
# ============================================================================


def test_account_detail_subclass():
    """Test AccountDetail extends Account with enrichment fields."""
    detail = AccountDetail.model_validate(
        {
            "id": "a_123",
            "name": "Acme Corp",
            "domain": "acme.com",
            "industries": ["saas", "fintech"],
            "technology_names": ["Python", "React"],
            "estimated_num_employees": 500,
            "annual_revenue": 10_000_000.0,
        }
    )
    assert isinstance(detail, Account)
    assert detail.name == "Acme Corp"
    assert detail.industries == ["saas", "fintech"]
    assert detail.technology_names == ["Python", "React"]
    assert detail.estimated_num_employees == 500
    assert detail.annual_revenue == 10_000_000.0


def test_account_detail_inherits_search_fields():
    """Test AccountDetail works with search-only fields too."""
    detail = AccountDetail.model_validate(
        {
            "id": "a_123",
            "account_stage_id": "stage_1",
            "num_contacts": 42,
        }
    )
    assert detail.account_stage_id == "stage_1"
    assert detail.num_contacts == 42
    assert detail.industries == []
    assert detail.estimated_num_employees is None


def test_account_detail_with_technologies():
    """Test AccountDetail deserializes current_technologies into Technology models."""
    detail = AccountDetail.model_validate(
        {
            "id": "a1",
            "current_technologies": [
                {"uid": "t1", "name": "Python", "category": "Languages"},
                {"uid": "t2", "name": "React", "category": "Frameworks"},
            ],
        }
    )
    assert len(detail.current_technologies) == 2
    assert isinstance(detail.current_technologies[0], Technology)
    assert detail.current_technologies[0].name == "Python"


def test_account_detail_with_org_refs():
    """Test AccountDetail deserializes organization references."""
    detail = AccountDetail.model_validate(
        {
            "id": "a1",
            "owned_by_organization": {"id": "org1", "name": "Parent Corp"},
            "suborganizations": [
                {"id": "sub1", "name": "Sub LLC", "website_url": "https://sub.com"},
            ],
        }
    )
    assert isinstance(detail.owned_by_organization, OrganizationRef)
    assert detail.owned_by_organization.name == "Parent Corp"
    assert isinstance(detail.suborganizations[0], OrganizationRef)


def test_account_detail_with_queues():
    """Test AccountDetail deserializes account_queues into AccountQueue models."""
    detail = AccountDetail.model_validate(
        {
            "id": "a1",
            "account_queues": [{"id": "q1", "name": "Sales Queue"}],
        }
    )
    assert len(detail.account_queues) == 1
    assert isinstance(detail.account_queues[0], AccountQueue)
    assert detail.account_queues[0].name == "Sales Queue"


# ============================================================================
# DEAL
# ============================================================================


def test_deal_model():
    """Test Deal model validation."""
    deal = Deal(
        id="deal_123",
        name="Big Deal",
        opportunity_stage_id="stage_456",
        stage_name="Negotiation",
    )
    assert deal.id == "deal_123"
    assert deal.name == "Big Deal"
    assert deal.opportunity_stage_id == "stage_456"
    assert deal.stage_name == "Negotiation"


def test_deal_extra_fields():
    """Test Deal model captures unknown API fields."""
    deal = Deal.model_validate({"id": "deal_123", "future_field": True})
    assert deal.model_extra == {"future_field": True}


def test_deal_with_currency():
    """Test Deal deserializes currency into Currency model."""
    deal = Deal.model_validate(
        {
            "id": "d1",
            "currency": {"name": "US Dollar", "iso_code": "USD", "symbol": "$"},
        }
    )
    assert isinstance(deal.currency, Currency)
    assert deal.currency.iso_code == "USD"


def test_deal_with_contact_roles():
    """Test Deal deserializes opportunity_contact_roles with typed role entries."""
    deal = Deal.model_validate(
        {
            "id": "d1",
            "opportunity_contact_roles": [
                {
                    "id": "r1",
                    "contact_id": "c1",
                    "is_primary": True,
                    "role": [
                        {
                            "opportunity_contact_role_type_id": "type1",
                            "is_primary": True,
                            "crm_role_id": None,
                        },
                    ],
                },
            ],
        }
    )
    assert len(deal.opportunity_contact_roles) == 1
    assert isinstance(deal.opportunity_contact_roles[0], OpportunityContactRole)
    assert deal.opportunity_contact_roles[0].is_primary is True
    assert len(deal.opportunity_contact_roles[0].role) == 1
    assert isinstance(deal.opportunity_contact_roles[0].role[0], OpportunityRoleEntry)
    assert deal.opportunity_contact_roles[0].role[0].opportunity_contact_role_type_id == "type1"


def test_deal_with_embedded_account():
    """Test Deal deserializes embedded account into Account model."""
    deal = Deal.model_validate(
        {
            "id": "d1",
            "account": {"id": "a1", "name": "Acme Corp"},
        }
    )
    assert isinstance(deal.account, Account)
    assert deal.account.name == "Acme Corp"


# ============================================================================
# OPPORTUNITY CONTACT ROLE TYPE
# ============================================================================


def test_opportunity_contact_role_type_model():
    """Test OpportunityContactRoleType model validation."""
    rt = OpportunityContactRoleType.model_validate(
        {
            "id": "rt1",
            "name": "Decision Maker",
            "team_id": "team1",
            "crm_api_name": None,
            "crm_label": None,
            "display_order": 3.0,
        }
    )
    assert rt.id == "rt1"
    assert rt.name == "Decision Maker"
    assert rt.display_order == 3.0


def test_opportunity_contact_role_type_minimal():
    """Test OpportunityContactRoleType with only required fields."""
    rt = OpportunityContactRoleType.model_validate({"id": "rt1"})
    assert rt.id == "rt1"
    assert rt.name is None
    assert rt.display_order is None


def test_opportunity_contact_role_role_type_id_property():
    """Test role_type_id convenience property returns first role type ID."""
    role = OpportunityContactRole.model_validate(
        {
            "id": "r1",
            "contact_id": "c1",
            "role": [
                {"opportunity_contact_role_type_id": "type1", "is_primary": True},
            ],
        }
    )
    assert role.role_type_id == "type1"


def test_opportunity_contact_role_role_type_id_empty():
    """Test role_type_id returns None when no roles assigned."""
    role = OpportunityContactRole.model_validate({"id": "r1", "role": []})
    assert role.role_type_id is None


# ============================================================================
# PIPELINE & STAGE
# ============================================================================


def test_pipeline_model():
    """Test Pipeline model validation."""
    pipeline = Pipeline(
        id="pipe_123",
        title="Sales Pipeline",
        default_pipeline=True,
    )
    assert pipeline.id == "pipe_123"
    assert pipeline.title == "Sales Pipeline"
    assert pipeline.default_pipeline is True


def test_stage_model():
    """Test Stage model validation."""
    stage = Stage(
        id="stage_123",
        name="Qualified",
        display_order=1.0,
        probability=75.0,
    )
    assert stage.id == "stage_123"
    assert stage.name == "Qualified"
    assert stage.probability == 75.0


# ============================================================================
# NOTE
# ============================================================================


def test_note_model():
    """Test Note model validation."""
    note = Note(
        id="note_123",
        title="Meeting Notes",
        content="Discussed Q1 goals",
        contact_ids=["contact_1"],
    )
    assert note.id == "note_123"
    assert note.title == "Meeting Notes"
    assert len(note.contact_ids) == 1


def test_note_optional_title_content():
    """Test Note.title and Note.content default to None for raw API usage."""
    note = Note(id="note_123")
    assert note.title is None
    assert note.content is None


def test_note_with_crm_notes():
    """Test Note deserializes crm_notes into CrmNote models."""
    note = Note.model_validate(
        {
            "id": "n1",
            "title": "Test",
            "content": "Body",
            "crm_notes": [
                {"id": "cn1", "crm_id": "hs_123", "source_cd": "hubspot", "crm_deleted": False},
            ],
        }
    )
    assert len(note.crm_notes) == 1
    assert isinstance(note.crm_notes[0], CrmNote)
    assert note.crm_notes[0].source_cd == "hubspot"


def test_note_pinned_to_top_defaults_to_none():
    """Test Note.pinned_to_top defaults to None (unknown), not False."""
    note = Note(id="n1")
    assert note.pinned_to_top is None


# ============================================================================
# CALL
# ============================================================================


def test_call_model():
    """Test Call model validation."""
    call = Call(
        id="call_123",
        contact_id="contact_1",
        caller_name="John Doe",
        duration=120,
        status="completed",
    )
    assert call.id == "call_123"
    assert call.caller_name == "John Doe"
    assert call.duration == 120


def test_call_with_embedded_contact():
    """Test Call deserializes embedded contact into Contact model."""
    call = Call.model_validate(
        {
            "id": "call_1",
            "contact": {"id": "c1", "name": "Jane Doe", "email": "jane@example.com"},
        }
    )
    assert isinstance(call.contact, Contact)
    assert call.contact.name == "Jane Doe"


# ============================================================================
# TASK
# ============================================================================


def test_base_task_model():
    """Test BaseTask model validation."""
    task = BaseTask(
        id="task_123",
        contact_id="contact_1",
        type="contact_action_item",
        priority="high",
        status="scheduled",
    )
    assert task.id == "task_123"
    assert task.contact_id == "contact_1"
    assert task.type == TaskType.CONTACT_ACTION_ITEM


def test_task_with_engagement_data():
    """Test LinkedInMessageTask deserializes engagement_data with typed types_count."""
    task = LinkedInMessageTask.model_validate(
        {
            "id": "t1",
            "engagement_data": {
                "_id": "ed1",
                "types_count": [
                    {"type_cd": "open", "count": 3},
                    {"type_cd": "reply", "count": 1},
                ],
                "last_engagement_date": "2025-02-14T10:33:27.000Z",
            },
        }
    )
    assert isinstance(task.engagement_data, EngagementData)
    assert isinstance(task.engagement_data.last_engagement_date, datetime)
    assert len(task.engagement_data.types_count) == 2
    assert isinstance(task.engagement_data.types_count[0], EngagementTypeCount)
    assert task.engagement_data.types_count[0].type_cd == "open"
    assert task.engagement_data.types_count[0].count == 3


def test_task_with_emailer_message():
    """Test EmailTask deserializes emailer_message into EmailerMessage model."""
    task = EmailTask.model_validate(
        {
            "id": "t1",
            "emailer_message": {
                "id": "em1",
                "subject": "Follow up",
                "status": "drafted",
                "to_email": "test@example.com",
                "from_email": "sender@example.com",
            },
        }
    )
    assert isinstance(task.emailer_message, EmailerMessage)
    assert task.emailer_message.subject == "Follow up"
    assert task.emailer_message.to_email == "test@example.com"


def test_task_emailer_message_without_id():
    """Test EmailerMessage accepts missing id (drafts may lack one)."""
    task = EmailTask.model_validate(
        {
            "id": "t1",
            "emailer_message": {
                "subject": "Draft",
                "status": "drafted",
            },
        }
    )
    assert isinstance(task.emailer_message, EmailerMessage)
    assert task.emailer_message.id is None
    assert task.emailer_message.subject == "Draft"


def test_task_email_type_enum():
    """Test TaskType.OUTREACH_MANUAL_EMAIL has correct value."""
    from qodev_apollo_api.models import TaskType

    assert TaskType.OUTREACH_MANUAL_EMAIL == "outreach_manual_email"
    assert TaskType.OUTREACH_MANUAL_EMAIL.value == "outreach_manual_email"


# ============================================================================
# resolve_task — discriminated union
# ============================================================================


def test_resolve_task_email():
    """Test resolve_task returns EmailTask for outreach_manual_email."""
    result = resolve_task({"id": "1", "type": "outreach_manual_email"})
    assert isinstance(result, EmailTask)


def test_resolve_task_linkedin_connect():
    """Test resolve_task returns LinkedInConnectTask."""
    result = resolve_task({"id": "1", "type": "linkedin_step_connect"})
    assert isinstance(result, LinkedInConnectTask)


def test_resolve_task_linkedin_message():
    """Test resolve_task returns LinkedInMessageTask."""
    result = resolve_task({"id": "1", "type": "linkedin_step_message"})
    assert isinstance(result, LinkedInMessageTask)


def test_resolve_task_call():
    """Test resolve_task returns CallTask."""
    result = resolve_task({"id": "1", "type": "call"})
    assert isinstance(result, CallTask)


def test_resolve_task_account_call():
    """Test resolve_task returns AccountCallTask."""
    result = resolve_task({"id": "1", "type": "account_call"})
    assert isinstance(result, AccountCallTask)


def test_resolve_task_contact_call():
    """Test resolve_task returns ContactCallTask."""
    result = resolve_task({"id": "1", "type": "contact_call"})
    assert isinstance(result, ContactCallTask)


def test_resolve_task_contact_action_item():
    """Test resolve_task returns ContactActionItemTask."""
    result = resolve_task({"id": "1", "type": "contact_action_item"})
    assert isinstance(result, ContactActionItemTask)


def test_resolve_task_account_action_item():
    """Test resolve_task returns AccountActionItemTask."""
    result = resolve_task({"id": "1", "type": "account_action_item"})
    assert isinstance(result, AccountActionItemTask)


def test_resolve_task_action_item():
    """Test resolve_task returns ActionItemTask."""
    result = resolve_task({"id": "1", "type": "action_item"})
    assert isinstance(result, ActionItemTask)


def test_resolve_task_linkedin_interact():
    """Test resolve_task returns LinkedInInteractTask."""
    result = resolve_task({"id": "1", "type": "linkedin_step_interact_post"})
    assert isinstance(result, LinkedInInteractTask)


def test_resolve_task_linkedin_view_profile():
    """Test resolve_task returns LinkedInViewProfileTask."""
    result = resolve_task({"id": "1", "type": "linkedin_step_view_profile"})
    assert isinstance(result, LinkedInViewProfileTask)


def test_resolve_task_linkedin_actions():
    """Test resolve_task returns LinkedInActionsTask."""
    result = resolve_task({"id": "1", "type": "linkedin_actions"})
    assert isinstance(result, LinkedInActionsTask)


def test_resolve_task_all_subtypes_are_base_task():
    """Test all resolve_task results are BaseTask subclasses."""
    for task_type in TaskType:
        result = resolve_task({"id": "1", "type": task_type.value})
        assert isinstance(result, BaseTask), f"{task_type} did not resolve to a BaseTask subclass"


def test_resolve_task_missing_type_raises():
    """Test resolve_task raises ValidationError when type is missing."""
    with pytest.raises(ValidationError):
        resolve_task({"id": "1", "status": "complete"})


def test_resolve_task_unknown_type_falls_back_to_other_task():
    """Test resolve_task falls back to OtherTask for unknown type values."""
    result = resolve_task({"id": "1", "type": "some_future_task_type"})
    assert isinstance(result, OtherTask)
    assert result.type == TaskType.OTHER
    assert result.original_type == "some_future_task_type"
    assert result.id == "1"


def test_task_with_full_emailer_message():
    """Test EmailTask with complete emailer_message including scheduling fields."""
    task = EmailTask.model_validate(
        {
            "id": "t1",
            "type": "outreach_manual_email",
            "emailer_message": {
                "id": "em1",
                "subject": "Follow up on our conversation",
                "body_text": "<p>Hello, just following up.</p>",
                "status": "drafted",
                "to_email": "recipient@example.com",
                "from_email": "sender@example.com",
                "due_at": "2026-02-19T10:00:00.000Z",
            },
        }
    )
    assert task.type == "outreach_manual_email"
    assert task.emailer_message is not None
    assert task.emailer_message.body_text == "<p>Hello, just following up.</p>"
    assert task.emailer_message.due_at is not None


def test_emailer_message_inherits_email_fields():
    """Test EmailerMessage has all Email fields available."""
    msg = EmailerMessage.model_validate(
        {
            "subject": "Test",
            "body_text": "Body",
            "status": "drafted",
            "cc_emails": ["cc@example.com"],
            "enable_tracking": True,
        }
    )
    assert msg.id is None
    assert msg.subject == "Test"
    assert msg.cc_emails == ["cc@example.com"]
    assert msg.enable_tracking is True


# ============================================================================
# EMAIL
# ============================================================================


def test_email_model():
    """Test Email model validation."""
    email = Email(
        id="email_123",
        contact_id="contact_1",
        subject="Hello",
        status="completed",
        to_email="test@example.com",
    )
    assert email.id == "email_123"
    assert email.subject == "Hello"
    assert email.to_email == "test@example.com"


def test_email_with_participants():
    """Test Email deserializes recipients and send_from into EmailParticipant models."""
    email = Email.model_validate(
        {
            "id": "e1",
            "send_from": {"email": "sender@example.com", "raw_name": "Sender"},
            "recipients": [
                {"email": "r1@example.com", "recipient_type_cd": "to"},
                {"email": "r2@example.com", "recipient_type_cd": "cc"},
            ],
        }
    )
    assert isinstance(email.send_from, EmailParticipant)
    assert email.send_from.email == "sender@example.com"
    assert len(email.recipients) == 2
    assert isinstance(email.recipients[0], EmailParticipant)
    assert email.recipients[1].recipient_type_cd == "cc"


# ============================================================================
# ENGAGEMENT GRAPH
# ============================================================================


def test_engagement_graph_entry():
    """Test EngagementGraphEntry model validation."""
    entry = EngagementGraphEntry.model_validate(
        {"year": 2025, "month": 6, "inbound": 3, "outbound": 7}
    )
    assert entry.year == 2025
    assert entry.month == 6
    assert entry.inbound == 3
    assert entry.outbound == 7


def test_contact_detail_with_engagement_graph():
    """Test ContactDetail deserializes engagement_graph into EngagementGraphEntry list."""
    detail = ContactDetail.model_validate(
        {
            "id": "c1",
            "engagement_graph": [
                {"year": 2025, "month": 1, "inbound": 2, "outbound": 5},
                {"year": 2025, "month": 2, "inbound": 0, "outbound": 3},
            ],
        }
    )
    assert detail.engagement_graph is not None
    assert len(detail.engagement_graph) == 2
    assert isinstance(detail.engagement_graph[0], EngagementGraphEntry)
    assert detail.engagement_graph[0].outbound == 5


# ============================================================================
# CONVERSATION MODELS
# ============================================================================


def test_conversation_participant():
    """Test ConversationParticipant model validation."""
    participant = ConversationParticipant.model_validate(
        {
            "id": "p1",
            "name": "Jan Scheffler",
            "email": "jan@example.com",
            "contact_id": "c1",
            "user_id": "u1",
            "is_internal_participant": True,
            "account_name": "qodev",
            "title": "Founder",
        }
    )
    assert participant.id == "p1"
    assert participant.name == "Jan Scheffler"
    assert participant.is_internal_participant is True


def test_transcript_segment():
    """Test TranscriptSegment model validation."""
    segment = TranscriptSegment.model_validate(
        {
            "id": "seg1",
            "start_time": 1600.0,
            "end_time": 1620.0,
            "spoken_sentence": "Hello, how are you?",
            "participant_id": "p1",
            "participant_name": "Jan",
        }
    )
    assert segment.start_time == 1600.0
    assert segment.spoken_sentence == "Hello, how are you?"
    assert segment.participant_name == "Jan"


def test_video_recording():
    """Test VideoRecording model validation."""
    recording = VideoRecording.model_validate(
        {"type_cd": "video", "url": "https://example.com/rec.mp4", "state_cd": "ready"}
    )
    assert recording.type_cd == "video"
    assert recording.url == "https://example.com/rec.mp4"


def test_call_summary_with_structured_items():
    """Test CallSummary with typed next_steps, pain_points, objections."""
    summary = CallSummary.model_validate(
        {
            "outcome": "Scheduled follow-up demo",
            "pricing_discussion": "Too expensive",
            "next_steps": [
                {
                    "id": "ns1",
                    "step": "Schedule demo",
                    "due_at": "2026-02-24T00:00:00Z",
                    "action_type": "action_item",
                    "participant_name": "Jan",
                },
            ],
            "pain_points": [
                {"id": "pp1", "text": "Catching bugs early", "participant_name": "Client"},
            ],
            "objections": [
                {"id": "obj1", "text": "Pricing too high", "organization_name": "ACME"},
            ],
        }
    )
    assert summary.outcome == "Scheduled follow-up demo"
    assert len(summary.next_steps) == 1
    assert isinstance(summary.next_steps[0], CallSummaryNextStep)
    assert summary.next_steps[0].step == "Schedule demo"
    assert summary.next_steps[0].due_at == datetime(2026, 2, 24, tzinfo=UTC)
    assert len(summary.pain_points) == 1
    assert isinstance(summary.pain_points[0], CallSummaryPoint)
    assert summary.pain_points[0].text == "Catching bugs early"
    assert len(summary.objections) == 1
    assert isinstance(summary.objections[0], CallSummaryPoint)
    assert summary.objections[0].organization_name == "ACME"


def test_call_summary_with_null_lists():
    """Test CallSummary accepts None for list fields (editable_call_summary case)."""
    summary = CallSummary.model_validate(
        {
            "outcome": "Good call",
            "next_steps": None,
            "pain_points": None,
            "objections": None,
        }
    )
    assert summary.outcome == "Good call"
    assert summary.next_steps is None
    assert summary.pain_points is None
    assert summary.objections is None


def test_call_summary_with_empty_lists():
    """Test CallSummary with empty lists (most conversations)."""
    summary = CallSummary.model_validate({"next_steps": [], "pain_points": [], "objections": []})
    assert summary.next_steps == []
    assert summary.pain_points == []
    assert summary.objections == []


def test_call_summary_defaults():
    """Test CallSummary with no fields provided."""
    summary = CallSummary.model_validate({})
    assert summary.outcome is None
    assert summary.next_steps is None
    assert summary.pain_points is None


def test_conversation_deal():
    """Test ConversationDeal model validation."""
    deal = ConversationDeal.model_validate(
        {
            "id": "d1",
            "name": "ACME / Product",
            "account_name": "ACME",
            "opportunity_stage_id": "stage1",
        }
    )
    assert deal.id == "d1"
    assert deal.name == "ACME / Product"
    assert deal.account_name == "ACME"


def test_conversation_from_search():
    """Test Conversation model with search endpoint data."""
    conv = Conversation.model_validate(
        {
            "id": "conv1",
            "start_time": "2026-02-18T14:03:39.421+00:00",
            "duration": 3439,
            "host": "Jan",
            "host_id": "u1",
            "state": "insights_generated",
            "conversation_type": "video_conference",
            "topic": "Product Demo",
            "comment_count": 2,
            "is_private": False,
            "participant_names": ["Jan", "Client"],
            "account_names": ["ACME"],
            "account_ids": ["acc1"],
            "participants_info": [
                {
                    "id": "p1",
                    "name": "Jan",
                    "email": "jan@example.com",
                    "is_internal_participant": True,
                },
                {
                    "id": "p2",
                    "name": "Client",
                    "email": "client@acme.com",
                    "is_internal_participant": False,
                },
            ],
            "deals": [
                {
                    "id": "d1",
                    "name": "ACME Deal",
                    "account_name": "ACME",
                    "opportunity_stage_id": "s1",
                },
            ],
        }
    )
    assert conv.id == "conv1"
    assert conv.duration == 3439
    assert conv.topic == "Product Demo"
    assert isinstance(conv.start_time, datetime)
    assert len(conv.participants_info) == 2
    assert isinstance(conv.participants_info[0], ConversationParticipant)
    assert conv.participants_info[1].name == "Client"
    assert len(conv.deals) == 1
    assert isinstance(conv.deals[0], ConversationDeal)
    assert conv.deals[0].name == "ACME Deal"


def test_conversation_minimal():
    """Test Conversation with only required fields."""
    conv = Conversation.model_validate({"id": "conv1"})
    assert conv.id == "conv1"
    assert conv.topic is None
    assert conv.participants_info == []
    assert conv.deals == []


def test_conversation_detail():
    """Test ConversationDetail inherits Conversation and adds detail fields."""
    detail = ConversationDetail.model_validate(
        {
            "id": "conv1",
            "topic": "Demo Call",
            "duration": 1800,
            "transcript": [
                {
                    "id": "seg1",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "spoken_sentence": "Hello everyone",
                    "participant_id": "p1",
                    "participant_name": "Jan",
                },
                {
                    "id": "seg2",
                    "start_time": 5.0,
                    "end_time": 10.0,
                    "spoken_sentence": "Thanks for joining",
                    "participant_id": "p2",
                    "participant_name": "Client",
                },
            ],
            "video_recording": {
                "type_cd": "video",
                "url": "https://example.com/rec.mp4",
                "state_cd": "ready",
            },
            "call_summary": {
                "outcome": "Positive demo",
                "next_steps": [{"id": "ns1", "step": "Send proposal", "participant_name": "Jan"}],
                "pain_points": [
                    {"id": "pp1", "text": "Manual process", "participant_name": "Client"}
                ],
                "objections": [],
            },
            "key_topics": {"tracker_insights": {"trackers_available": True, "trackers": []}},
            "pushed_to_crm": False,
            "is_clip": False,
            "opportunity_ids": ["opp1", "opp2"],
        }
    )
    # Inherited fields
    assert detail.id == "conv1"
    assert detail.topic == "Demo Call"
    assert detail.duration == 1800

    # Detail-specific fields
    assert len(detail.transcript) == 2
    assert isinstance(detail.transcript[0], TranscriptSegment)
    assert detail.transcript[0].spoken_sentence == "Hello everyone"

    assert isinstance(detail.video_recording, VideoRecording)
    assert detail.video_recording.type_cd == "video"

    assert isinstance(detail.call_summary, CallSummary)
    assert detail.call_summary.outcome == "Positive demo"
    assert len(detail.call_summary.next_steps) == 1
    assert detail.call_summary.next_steps[0].step == "Send proposal"

    assert detail.key_topics == {"tracker_insights": {"trackers_available": True, "trackers": []}}
    assert detail.pushed_to_crm is False
    assert detail.opportunity_ids == ["opp1", "opp2"]


def test_conversation_detail_minimal():
    """Test ConversationDetail with only required fields."""
    detail = ConversationDetail.model_validate({"id": "conv1"})
    assert detail.transcript == []
    assert detail.video_recording is None
    assert detail.call_summary is None
    assert detail.key_topics == {}
    assert detail.opportunity_ids == []


def test_conversation_detail_with_editable_summary_null_fields():
    """Test ConversationDetail where editable_call_summary has null list fields."""
    detail = ConversationDetail.model_validate(
        {
            "id": "conv1",
            "editable_call_summary": {
                "outcome": "Good call",
                "pain_points": None,
                "objections": None,
            },
        }
    )
    assert detail.editable_call_summary is not None
    assert detail.editable_call_summary.outcome == "Good call"
    assert detail.editable_call_summary.pain_points is None
    assert detail.editable_call_summary.objections is None


# ============================================================================
# PAGINATED RESPONSE
# ============================================================================


def test_paginated_response():
    """Test PaginatedResponse generic model."""
    contacts = [
        Contact(id="1", name="John"),
        Contact(id="2", name="Jane"),
    ]

    response = PaginatedResponse[Contact](
        items=contacts,
        total=2,
        page=1,
    )

    assert len(response.items) == 2
    assert response.total == 2
    assert response.page == 1
    assert isinstance(response.items[0], Contact)
