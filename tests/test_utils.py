"""Unit tests for the utils module."""

from blogmore.utils import normalize_site_url


class TestNormalizeSiteUrl:
    """Test the normalize_site_url function."""

    def test_normalize_no_trailing_slash(self) -> None:
        """Test normalizing URL without trailing slash."""
        assert normalize_site_url("https://example.com") == "https://example.com"

    def test_normalize_with_trailing_slash(self) -> None:
        """Test normalizing URL with trailing slash."""
        assert normalize_site_url("https://example.com/") == "https://example.com"

    def test_normalize_multiple_trailing_slashes(self) -> None:
        """Test normalizing URL with multiple trailing slashes."""
        assert normalize_site_url("https://example.com///") == "https://example.com"

    def test_normalize_empty_string(self) -> None:
        """Test normalizing empty string."""
        assert normalize_site_url("") == ""

    def test_normalize_just_slash(self) -> None:
        """Test normalizing just a slash."""
        assert normalize_site_url("/") == ""

    def test_normalize_http_url(self) -> None:
        """Test normalizing HTTP URL with trailing slash."""
        assert normalize_site_url("http://blog.davep.org/") == "http://blog.davep.org"

    def test_normalize_https_url(self) -> None:
        """Test normalizing HTTPS URL with trailing slash."""
        assert (
            normalize_site_url("https://blog.davep.org/") == "https://blog.davep.org"
        )
