"""Tests for Apollo models."""

from apollo.models import Account, Contact, Deal, Note, PaginatedResponse, Pipeline, Stage


def test_contact_model():
    """Test Contact model validation."""
    contact = Contact(
        id="test_id",
        name="John Doe",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        title="CEO",
        company="Example Corp",
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


def test_account_model():
    """Test Account model validation."""
    account = Account(
        id="acc_123",
        name="Example Corp",
        domain="example.com",
        employees=50,
    )
    assert account.id == "acc_123"
    assert account.name == "Example Corp"
    assert account.domain == "example.com"
    assert account.employees == 50


def test_deal_model():
    """Test Deal model validation."""
    deal = Deal(
        id="deal_123",
        name="Big Deal",
        stage="Negotiation",
    )
    assert deal.id == "deal_123"
    assert deal.name == "Big Deal"
    assert deal.stage == "Negotiation"


def test_pipeline_model():
    """Test Pipeline model validation."""
    pipeline = Pipeline(
        id="pipe_123",
        title="Sales Pipeline",
        is_default=True,
    )
    assert pipeline.id == "pipe_123"
    assert pipeline.title == "Sales Pipeline"
    assert pipeline.is_default is True


def test_stage_model():
    """Test Stage model validation."""
    stage = Stage(
        id="stage_123",
        name="Qualified",
        display_order=1,
        probability=75,
    )
    assert stage.id == "stage_123"
    assert stage.name == "Qualified"
    assert stage.probability == 75


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
