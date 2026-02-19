"""Unit tests for the utils module."""

from blogmore.utils import (
    calculate_reading_time,
    make_urls_absolute,
    normalize_site_url,
)


class TestCalculateReadingTime:
    """Test the calculate_reading_time function."""

    def test_calculate_reading_time_short_text(self) -> None:
        """Test that short text returns at least 1 minute."""
        assert calculate_reading_time("Hello world") == 1

    def test_calculate_reading_time_medium_text(self) -> None:
        """Test calculating reading time for medium text."""
        # 400 words at 200 WPM = 2 minutes
        content = " ".join(["word"] * 400)
        assert calculate_reading_time(content) == 2

    def test_calculate_reading_time_long_text(self) -> None:
        """Test calculating reading time for longer text."""
        # 1000 words at 200 WPM = 5 minutes
        content = " ".join(["word"] * 1000)
        assert calculate_reading_time(content) == 5

    def test_calculate_reading_time_with_markdown_formatting(self) -> None:
        """Test that markdown formatting is stripped before counting."""
        content = "**Bold text** and *italic text* and `code` and [link text](url)"
        # Should count: Bold text and italic text and code and link text = 10 words
        assert calculate_reading_time(content) == 1

    def test_calculate_reading_time_with_code_blocks(self) -> None:
        """Test that code blocks are removed before counting."""
        content = """
        This is some text before the code.
        
        ```python
        def hello():
            print("This code should not be counted")
            return "lots of words here"
        ```
        
        This is text after the code.
        """
        # Should count: "This is some text before the code" (7) + "This is text after the code" (6) = 13 words
        assert calculate_reading_time(content) == 1

    def test_calculate_reading_time_with_inline_code(self) -> None:
        """Test that inline code is removed."""
        content = "Use the `calculate_reading_time` function to get the time."
        # Should count: "Use the function to get the time" = 7 words
        assert calculate_reading_time(content) == 1

    def test_calculate_reading_time_with_images(self) -> None:
        """Test that markdown images are ignored."""
        content = "Here is an image: ![Alt text](image.jpg) and some more text."
        # Should count: "Here is an image and some more text" = 8 words
        assert calculate_reading_time(content) == 1

    def test_calculate_reading_time_with_html_tags(self) -> None:
        """Test that HTML tags are removed."""
        content = "<p>This is a paragraph</p> with <strong>HTML tags</strong>."
        # Should count: "This is a paragraph with HTML tags" = 7 words
        assert calculate_reading_time(content) == 1

    def test_calculate_reading_time_custom_wpm(self) -> None:
        """Test using a custom words per minute rate."""
        # 200 words at 100 WPM = 2 minutes
        content = " ".join(["word"] * 200)
        assert calculate_reading_time(content, words_per_minute=100) == 2

    def test_calculate_reading_time_rounding(self) -> None:
        """Test that reading time rounds to nearest minute."""
        # 250 words at 200 WPM = 1.25 minutes, should round to 1
        content = " ".join(["word"] * 250)
        assert calculate_reading_time(content) == 1

        # 350 words at 200 WPM = 1.75 minutes, should round to 2
        content = " ".join(["word"] * 350)
        assert calculate_reading_time(content) == 2

    def test_calculate_reading_time_empty_string(self) -> None:
        """Test that empty content returns 1 minute."""
        assert calculate_reading_time("") == 1

    def test_calculate_reading_time_only_formatting(self) -> None:
        """Test content with only formatting characters."""
        content = "***___```###"
        assert calculate_reading_time(content) == 1


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
        assert normalize_site_url("https://blog.davep.org/") == "https://blog.davep.org"


class TestMakeUrlsAbsolute:
    """Test the make_urls_absolute function."""

    def test_src_double_quotes(self) -> None:
        """Test that src with double-quoted relative path is rewritten."""
        html = '<img src="/images/photo.jpg">'
        result = make_urls_absolute(html, "https://example.com")
        assert result == '<img src="https://example.com/images/photo.jpg">'

    def test_src_single_quotes(self) -> None:
        """Test that src with single-quoted relative path is rewritten."""
        html = "<img src='/images/photo.jpg'>"
        result = make_urls_absolute(html, "https://example.com")
        assert result == "<img src='https://example.com/images/photo.jpg'>"

    def test_href_double_quotes(self) -> None:
        """Test that href with double-quoted relative path is rewritten."""
        html = '<a href="/about.html">About</a>'
        result = make_urls_absolute(html, "https://example.com")
        assert result == '<a href="https://example.com/about.html">About</a>'

    def test_href_single_quotes(self) -> None:
        """Test that href with single-quoted relative path is rewritten."""
        html = "<a href='/about.html'>About</a>"
        result = make_urls_absolute(html, "https://example.com")
        assert result == "<a href='https://example.com/about.html'>About</a>"

    def test_absolute_urls_unchanged(self) -> None:
        """Test that existing absolute URLs are not modified."""
        html = '<img src="https://cdn.example.com/images/photo.jpg">'
        result = make_urls_absolute(html, "https://example.com")
        assert result == html

    def test_absolute_http_urls_unchanged(self) -> None:
        """Test that existing absolute HTTP URLs are not modified."""
        html = '<a href="http://external.com/page.html">link</a>'
        result = make_urls_absolute(html, "https://example.com")
        assert result == html

    def test_multiple_attributes_in_one_call(self) -> None:
        """Test that multiple relative attributes are all rewritten."""
        html = (
            '<img src="/img/banner.png">'
            '<a href="/posts/hello.html">Hello</a>'
        )
        result = make_urls_absolute(html, "https://example.com")
        assert 'src="https://example.com/img/banner.png"' in result
        assert 'href="https://example.com/posts/hello.html"' in result

    def test_trailing_slash_stripped_from_base_url(self) -> None:
        """Test that a trailing slash on base_url does not produce double slashes."""
        html = '<img src="/img/photo.jpg">'
        result = make_urls_absolute(html, "https://example.com/")
        assert result == '<img src="https://example.com/img/photo.jpg">'

    def test_deeply_nested_path(self) -> None:
        """Test rewriting a deeply nested root-relative path."""
        html = '<img src="/attachments/2026/02/11/banner.png">'
        result = make_urls_absolute(html, "https://myblog.com")
        assert result == '<img src="https://myblog.com/attachments/2026/02/11/banner.png">'

    def test_no_relative_urls_returns_unchanged(self) -> None:
        """Test that HTML with no relative URLs is returned unchanged."""
        html = "<p>Hello world</p>"
        result = make_urls_absolute(html, "https://example.com")
        assert result == html

    def test_parenthesised_href_made_absolute(self) -> None:
        """Test that root-relative href wrapped in parentheses is rewritten.

        Markdown typos like [text]((/path)) render to href="(/path)" which is
        still a relative URL reference that feed validators will flag.
        """
        html = '<a href="(/2024/08/18/paindrop.html)">the other post</a>'
        result = make_urls_absolute(html, "https://blog.davep.org")
        assert result == '<a href="https://blog.davep.org/2024/08/18/paindrop.html">the other post</a>'

    def test_parenthesised_src_made_absolute(self) -> None:
        """Test that root-relative src wrapped in parentheses is rewritten."""
        html = "<img src='(/img/photo.jpg)'>"
        result = make_urls_absolute(html, "https://example.com")
        assert result == "<img src='https://example.com/img/photo.jpg'>"

    def test_parenthesised_absolute_url_unchanged(self) -> None:
        """Test that an absolute URL wrapped in parentheses is not modified."""
        html = '<a href="(https://external.com/path)">link</a>'
        result = make_urls_absolute(html, "https://example.com")
        assert result == html
