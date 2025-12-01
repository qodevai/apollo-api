"""Tests for Apollo exceptions."""

from apollo.exceptions import APIError, ApolloError, AuthenticationError, RateLimitError


def test_apollo_error_base():
    """Test base ApolloError."""
    error = ApolloError("Something went wrong")
    assert str(error) == "Something went wrong"
    assert isinstance(error, Exception)


def test_authentication_error():
    """Test AuthenticationError."""
    error = AuthenticationError("Invalid API key")
    assert str(error) == "Invalid API key"
    assert isinstance(error, ApolloError)


def test_rate_limit_error():
    """Test RateLimitError with retry_after."""
    error = RateLimitError("Rate limit exceeded", retry_after=3600)
    assert str(error) == "Rate limit exceeded"
    assert error.retry_after == 3600
    assert isinstance(error, ApolloError)


def test_rate_limit_error_without_retry():
    """Test RateLimitError without retry_after."""
    error = RateLimitError("Rate limit exceeded")
    assert str(error) == "Rate limit exceeded"
    assert error.retry_after is None


def test_api_error():
    """Test APIError with status code."""
    error = APIError("Bad request", status_code=400)
    assert str(error) == "Bad request"
    assert error.status_code == 400
    assert isinstance(error, ApolloError)


def test_api_error_without_status():
    """Test APIError without status code."""
    error = APIError("Unknown error")
    assert str(error) == "Unknown error"
    assert error.status_code is None
