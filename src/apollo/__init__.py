"""Apollo.io API Client.

Async Python client for Apollo.io CRM API with full type safety.
"""

from .client import ApolloClient
from .exceptions import APIError, ApolloError, AuthenticationError, RateLimitError
from .models import (
    Account,
    Call,
    Contact,
    Deal,
    Email,
    EmploymentHistory,
    JobPosting,
    NewsArticle,
    Note,
    PaginatedResponse,
    Pipeline,
    Stage,
    Task,
)

__all__ = [
    "APIError",
    "Account",
    "ApolloClient",
    "ApolloError",
    "AuthenticationError",
    "Call",
    "Contact",
    "Deal",
    "Email",
    "EmploymentHistory",
    "JobPosting",
    "NewsArticle",
    "Note",
    "PaginatedResponse",
    "Pipeline",
    "RateLimitError",
    "Stage",
    "Task",
]

__version__ = "0.1.0"
