"""Unit tests for the responsive_images module."""

from __future__ import annotations

from blogmore.image_optimizer import ImageVariant
from blogmore.responsive_images import rewrite_img_tags

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_variants(url_base: str, stem: str, widths: list[int]) -> list[ImageVariant]:
    """Return a list of dummy WebP ImageVariant objects."""
    return [
        ImageVariant(
            url=f"{url_base}/{stem}-{w}w.webp",
            width=w,
            mime_type="image/webp",
        )
        for w in widths
    ]


# ---------------------------------------------------------------------------
# rewrite_img_tags
# ---------------------------------------------------------------------------


class TestRewriteImgTags:
    """Test the rewrite_img_tags function."""

    def test_rewrites_known_image_to_picture(self) -> None:
        """Test that a matched <img> is wrapped in a <picture> element."""
        html = '<img src="/images/photo.jpg" alt="A photo">'
        variants = _make_variants("/images", "photo", [480, 768])
        result = rewrite_img_tags(html, {"/images/photo.jpg": variants})

        assert result.startswith("<picture>")
        assert result.endswith("</picture>")

    def test_picture_contains_webp_source(self) -> None:
        """Test that the <picture> element contains a WebP <source> tag."""
        html = '<img src="/images/photo.jpg" alt="Photo">'
        variants = _make_variants("/images", "photo", [480, 768])
        result = rewrite_img_tags(html, {"/images/photo.jpg": variants})

        assert 'type="image/webp"' in result
        assert "srcset=" in result

    def test_srcset_contains_all_variants(self) -> None:
        """Test that the srcset lists all generated variants."""
        html = '<img src="/images/photo.jpg" alt="Photo">'
        variants = _make_variants("/images", "photo", [480, 768, 1200])
        result = rewrite_img_tags(html, {"/images/photo.jpg": variants})

        assert "/images/photo-480w.webp 480w" in result
        assert "/images/photo-768w.webp 768w" in result
        assert "/images/photo-1200w.webp 1200w" in result

    def test_original_img_preserved_as_fallback(self) -> None:
        """Test that the original <img> tag is kept inside <picture>."""
        html = '<img src="/images/photo.jpg" alt="A photo">'
        variants = _make_variants("/images", "photo", [480])
        result = rewrite_img_tags(html, {"/images/photo.jpg": variants})

        # The fallback <img> with the original src should still be present.
        assert 'src="/images/photo.jpg"' in result
        assert 'alt="A photo"' in result

    def test_adds_lazy_loading_to_rewritten_img(self) -> None:
        """Test that loading=lazy is added to the fallback <img>."""
        html = '<img src="/images/photo.jpg" alt="Photo">'
        variants = _make_variants("/images", "photo", [480])
        result = rewrite_img_tags(html, {"/images/photo.jpg": variants})

        assert 'loading="lazy"' in result

    def test_does_not_add_duplicate_loading_attribute(self) -> None:
        """Test that an existing loading attribute is not duplicated."""
        html = '<img src="/images/photo.jpg" alt="Photo" loading="eager">'
        variants = _make_variants("/images", "photo", [480])
        result = rewrite_img_tags(html, {"/images/photo.jpg": variants})

        assert result.count("loading=") == 1

    def test_adds_lazy_loading_to_unmatched_img(self) -> None:
        """Test that loading=lazy is also added to images without variants."""
        html = '<img src="/images/other.jpg" alt="Other">'
        result = rewrite_img_tags(html, {})

        # No <picture> wrapper, but lazy loading should be added.
        assert "<picture>" not in result
        assert 'loading="lazy"' in result

    def test_unmatched_image_not_wrapped(self) -> None:
        """Test that <img> tags for unknown images are not wrapped."""
        html = '<img src="/images/unprocessed.jpg" alt="Other">'
        result = rewrite_img_tags(html, {})

        assert "<picture>" not in result
        assert "<img" in result

    def test_multiple_images_all_rewritten(self) -> None:
        """Test that all matching <img> tags in the document are rewritten."""
        html = '<img src="/a.jpg" alt="A"><img src="/b.jpg" alt="B">'
        variants_a = _make_variants("", "a", [480])
        variants_b = _make_variants("", "b", [480])
        result = rewrite_img_tags(html, {"/a.jpg": variants_a, "/b.jpg": variants_b})

        assert result.count("<picture>") == 2
        assert result.count("</picture>") == 2

    def test_empty_variants_list_not_wrapped(self) -> None:
        """Test that a key with an empty variants list does not produce a <picture>."""
        html = '<img src="/images/tiny.jpg" alt="Tiny">'
        # The image is in the map but has no variants (e.g. source was too small).
        result = rewrite_img_tags(html, {"/images/tiny.jpg": []})

        assert "<picture>" not in result
        assert 'loading="lazy"' in result

    def test_empty_html_returns_empty_string(self) -> None:
        """Test that empty input returns an empty string."""
        assert rewrite_img_tags("", {}) == ""

    def test_html_without_images_unchanged_except_lazy(self) -> None:
        """Test that HTML with no <img> tags is returned unchanged."""
        html = "<p>No images here.</p>"
        result = rewrite_img_tags(html, {})
        assert result == html

    def test_preserves_surrounding_html(self) -> None:
        """Test that non-img HTML is preserved around the rewritten element."""
        html = '<p>Before <img src="/images/photo.jpg" alt="P"> After</p>'
        variants = _make_variants("/images", "photo", [480])
        result = rewrite_img_tags(html, {"/images/photo.jpg": variants})

        assert result.startswith("<p>Before ")
        assert result.endswith(" After</p>")

    def test_single_quoted_src_matched(self) -> None:
        """Test that a src attribute using single quotes is still matched."""
        html = "<img src='/images/photo.jpg' alt='Photo'>"
        variants = _make_variants("/images", "photo", [480])
        result = rewrite_img_tags(html, {"/images/photo.jpg": variants})

        assert "<picture>" in result


# ---------------------------------------------------------------------------
# Relative src normalisation (bare-relative paths)
# ---------------------------------------------------------------------------


class TestRewriteImgTagsRelativeSrc:
    """Test that src values without a leading slash are matched correctly."""

    def test_bare_relative_src_matches_root_relative_key(self) -> None:
        """A src without a leading slash must match a root-relative dict key."""
        # Markdown: ![alt](attachments/photo.jpg) → src="attachments/photo.jpg"
        html = '<img src="attachments/photo.jpg" alt="Alt">'
        variants = _make_variants("/attachments", "photo", [480])
        result = rewrite_img_tags(html, {"/attachments/photo.jpg": variants})

        assert "<picture>" in result
        assert "photo-480w.webp" in result

    def test_bare_relative_src_original_preserved_in_fallback(self) -> None:
        """The original (unmodified) src value must appear in the fallback img."""
        html = '<img src="attachments/photo.jpg" alt="Alt">'
        variants = _make_variants("/attachments", "photo", [480])
        result = rewrite_img_tags(html, {"/attachments/photo.jpg": variants})

        # The original relative src must be kept as-is in the fallback.
        assert 'src="attachments/photo.jpg"' in result

    def test_root_relative_src_still_matched(self) -> None:
        """A src that already has a leading slash must continue to work."""
        html = '<img src="/attachments/photo.jpg" alt="Alt">'
        variants = _make_variants("/attachments", "photo", [480])
        result = rewrite_img_tags(html, {"/attachments/photo.jpg": variants})

        assert "<picture>" in result

    def test_absolute_http_url_not_rewritten(self) -> None:
        """A fully-qualified http URL must never match a root-relative key."""
        html = '<img src="https://example.com/photo.jpg" alt="Alt">'
        variants = _make_variants("/", "photo", [480])
        result = rewrite_img_tags(html, {"/photo.jpg": variants})

        assert "<picture>" not in result
        assert 'loading="lazy"' in result

    def test_data_uri_not_rewritten(self) -> None:
        """A data: URI must not be treated as a relative path."""
        html = '<img src="data:image/png;base64,abc" alt="Alt">'
        result = rewrite_img_tags(html, {"/data:image/png;base64,abc": []})

        assert "<picture>" not in result

    def test_nested_relative_path_matched(self) -> None:
        """A multi-level bare-relative path must match its root-relative key."""
        html = '<img src="attachments/2022/11/26/shot.webp" alt="S">'
        variants = _make_variants("/attachments/2022/11/26", "shot", [480])
        result = rewrite_img_tags(
            html, {"/attachments/2022/11/26/shot.webp": variants}
        )

        assert "<picture>" in result

