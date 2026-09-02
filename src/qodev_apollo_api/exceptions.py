"""Exceptions for Apollo client."""


class ApolloError(Exception):
    """Base exception for Apollo client."""


class AuthenticationError(ApolloError):
    """Raised when API authentication fails (401)."""


class RateLimitError(ApolloError):
    """Raised when rate limit exceeded (429).

    Apollo meters **per endpoint**, not per account: one endpoint can be fully
    exhausted while others on the same key are untouched. The message names the
    endpoint and which window ran out, and ``limits`` carries the parsed
    headers so a caller can pace itself instead of guessing.
    """

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        endpoint: str | None = None,
        limits: dict[str, int | None] | None = None,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds until rate limit resets (if provided by API)
            endpoint: The endpoint whose bucket was exhausted
            limits: Parsed rate-limit headers; a value of None means the header
                was absent, which is NOT the same as a bucket reading zero.
        """
        self.retry_after = retry_after
        self.endpoint = endpoint
        self.limits = limits or {}
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


class RoleAssignmentError(ApolloError):
    """Raised when ``update_opportunity_roles`` can't confirm its write stuck.

    Apollo's ``/opportunities/update_roles`` has been observed to return 200
    with the deal JSON while **not** persisting the write (a read-back minutes
    later showed 0 roles; the identical call succeeded on retry). The write
    response can't be trusted on its own, so ``update_opportunity_roles``
    always re-reads the opportunity afterwards and raises this instead of
    silently returning stale/wrong role data when a requested role is missing.
    """

    def __init__(self, message: str, opportunity_id: str, missing_contact_ids: list[str]):
        """Initialize role assignment error.

        Args:
            message: Error message.
            opportunity_id: The opportunity/deal ID the write targeted.
            missing_contact_ids: Requested contact IDs absent from the read-back.
        """
        self.opportunity_id = opportunity_id
        self.missing_contact_ids = missing_contact_ids
        super().__init__(message)
