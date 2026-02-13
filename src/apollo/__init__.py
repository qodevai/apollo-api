"""Apollo.io API Client.

Async Python client for Apollo.io CRM API with full type safety.
"""

from .client import ApolloClient
from .exceptions import APIError, ApolloError, AuthenticationError, RateLimitError
from .models import (
    Account,
    AccountDetail,
    ApolloModel,
    Call,
    Contact,
    ContactCampaignStatus,
    ContactDetail,
    CrmJob,
    CrmNote,
    Currency,
    Deal,
    Email,
    EmailParticipant,
    EmploymentHistory,
    EngagementData,
    JobPosting,
    NewsArticle,
    Note,
    OpportunityContactRole,
    OrganizationRef,
    PaginatedResponse,
    PhoneEntry,
    Pipeline,
    Stage,
    Task,
    Technology,
)

__all__ = [
    "APIError",
    "Account",
    "AccountDetail",
    "ApolloClient",
    "ApolloError",
    "ApolloModel",
    "AuthenticationError",
    "Call",
    "Contact",
    "ContactCampaignStatus",
    "ContactDetail",
    "CrmJob",
    "CrmNote",
    "Currency",
    "Deal",
    "Email",
    "EmailParticipant",
    "EmploymentHistory",
    "EngagementData",
    "JobPosting",
    "NewsArticle",
    "Note",
    "OpportunityContactRole",
    "OrganizationRef",
    "PaginatedResponse",
    "PhoneEntry",
    "Pipeline",
    "RateLimitError",
    "Stage",
    "Task",
    "Technology",
]

__version__ = "0.1.0"
