"""Exceptions for Apollo client."""


class ApolloError(Exception):
    """Base exception for Apollo client."""


class AuthenticationError(ApolloError):
    """Raised when API authentication fails (401)."""


class RateLimitError(ApolloError):
    """Raised when rate limit exceeded (429)."""

    def __init__(self, message: str, retry_after: int | None = None):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds until rate limit resets (if provided by API)
        """
        self.retry_after = retry_after
        super().__init__(message)


class APIError(ApolloError):
    """Raised for other API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code (if available)
        """
        self.status_code = status_code
        super().__init__(message)
