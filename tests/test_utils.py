"""Unit tests for the utils module."""

from blogmore.utils import (
    calculate_reading_time_from_html,
    count_words_from_html,
    make_urls_absolute,
    normalize_site_url,
)


class TestCalculateReadingTime:
    """Test the calculate_reading_time_from_html function."""

    def test_calculate_reading_time_short_text(self) -> None:
        """Test that short text returns at least 1 minute."""
        assert calculate_reading_time_from_html("<p>Hello world</p>") == 1

    def test_calculate_reading_time_medium_text(self) -> None:
        """Test calculating reading time for medium text."""
        # 400 words at 200 WPM = 2 minutes
        content = "<p>" + " ".join(["word"] * 400) + "</p>"
        assert calculate_reading_time_from_html(content) == 2

    def test_calculate_reading_time_long_text(self) -> None:
        """Test calculating reading time for longer text."""
        # 1000 words at 200 WPM = 5 minutes
        content = "<p>" + " ".join(["word"] * 1000) + "</p>"
        assert calculate_reading_time_from_html(content) == 5

    def test_calculate_reading_time_with_html_formatting(self) -> None:
        """Test that HTML formatting is stripped before counting."""
        content = (
            "<p><strong>Bold text</strong> and <em>italic text</em> and "
            "<code>code</code> and <a href='url'>link text</a></p>"
        )
        # Should count: Bold text and italic text and code and link text = 10 words
        assert calculate_reading_time_from_html(content) == 1

    def test_calculate_reading_time_with_code_blocks(self) -> None:
        """Test that code blocks are removed before counting."""
        content = """
        <p>This is some text before the code.</p>
        <pre><code class="language-python">
        def hello():
            print("This code should not be counted")
            return "lots of words here"
        </code></pre>
        <p>This is text after the code.</p>
        """
        # Should count: "This is some text before the code" (7) + "This is text after the code" (6) = 13 words
        assert calculate_reading_time_from_html(content) == 1

    def test_calculate_reading_time_with_inline_code(self) -> None:
        """Test that inline code text is included in the word count."""
        content = "<p>Use the <code>calculate_reading_time</code> function to get the time.</p>"
        # Inline code text is preserved; all words contribute to the count
        assert calculate_reading_time_from_html(content) == 1

    def test_calculate_reading_time_with_images(self) -> None:
        """Test that HTML images are ignored."""
        content = "<p>Here is an image: <img src='image.jpg' alt='Alt text'> and some more text.</p>"
        # Should count: "Here is an image and some more text" = 8 words
        assert calculate_reading_time_from_html(content) == 1

    def test_calculate_reading_time_with_html_tags(self) -> None:
        """Test that HTML tags are removed."""
        content = "<p>This is a paragraph</p> with <strong>HTML tags</strong>."
        # Should count: "This is a paragraph with HTML tags" = 7 words
        assert calculate_reading_time_from_html(content) == 1

    def test_calculate_reading_time_custom_wpm(self) -> None:
        """Test using a custom words per minute rate."""
        # 200 words at 100 WPM = 2 minutes
        content = "<p>" + " ".join(["word"] * 200) + "</p>"
        assert calculate_reading_time_from_html(content, words_per_minute=100) == 2

    def test_calculate_reading_time_rounding(self) -> None:
        """Test that reading time rounds to nearest minute."""
        # 250 words at 200 WPM = 1.25 minutes, should round to 1
        content = "<p>" + " ".join(["word"] * 250) + "</p>"
        assert calculate_reading_time_from_html(content) == 1

        # 350 words at 200 WPM = 1.75 minutes, should round to 2
        content = "<p>" + " ".join(["word"] * 350) + "</p>"
        assert calculate_reading_time_from_html(content) == 2

    def test_calculate_reading_time_empty_string(self) -> None:
        """Test that empty content returns 1 minute."""
        assert calculate_reading_time_from_html("") == 1

    def test_calculate_reading_time_only_tags(self) -> None:
        """Test content with only HTML tags."""
        content = "<div><span></span></div>"
        assert calculate_reading_time_from_html(content) == 1


class TestCountWordsFromHtml:
    """Test the count_words_from_html function."""

    def test_count_words_simple(self) -> None:
        """Test counting words in simple HTML."""
        assert count_words_from_html("<p>Hello world</p>") == 2

    def test_count_words_with_code_blocks(self) -> None:
        """Test that code blocks are excluded from word count."""
        content = """
        <p>Prose here.</p>
        <pre><code>
        ignored code block
        </code></pre>
        <p>More prose.</p>
        """
        assert count_words_from_html(content) == 4

    def test_count_words_with_inline_code(self) -> None:
        """Test that inline code is included in word count."""
        content = "<p>Prose with <code>inline code</code>.</p>"
        assert count_words_from_html(content) == 4


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
        html = '<img src="/img/banner.png"><a href="/posts/hello.html">Hello</a>'
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
        assert (
            result == '<img src="https://myblog.com/attachments/2026/02/11/banner.png">'
        )

    def test_no_relative_urls_returns_unchanged(self) -> None:
        """Test that HTML with no relative URLs is returned unchanged."""
        html = "<p>Hello world</p>"
        result = make_urls_absolute(html, "https://example.com")
        assert result == html


### test_utils.py ends here
