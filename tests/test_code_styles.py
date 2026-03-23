"""Tests for the code_styles module."""

from pathlib import Path

from blogmore.code_styles import (
    DEFAULT_DARK_STYLE,
    DEFAULT_LIGHT_STYLE,
    _colour_scheme_for_style,
    build_code_css,
    is_valid_style,
)


class TestIsValidStyle:
    """Tests for the is_valid_style function."""

    def test_default_style_is_valid(self) -> None:
        """The Pygments 'default' style is valid."""
        assert is_valid_style("default") is True

    def test_monokai_style_is_valid(self) -> None:
        """The Pygments 'monokai' style is valid."""
        assert is_valid_style("monokai") is True

    def test_friendly_style_is_valid(self) -> None:
        """The Pygments 'friendly' style is valid."""
        assert is_valid_style("friendly") is True

    def test_invalid_style_returns_false(self) -> None:
        """An unrecognised style name returns False."""
        assert is_valid_style("this-does-not-exist") is False

    def test_empty_string_is_invalid(self) -> None:
        """An empty string is not a valid style name."""
        assert is_valid_style("") is False

    def test_default_light_style_constant_is_valid(self) -> None:
        """The DEFAULT_LIGHT_STYLE constant is a valid Pygments style."""
        assert is_valid_style(DEFAULT_LIGHT_STYLE) is True

    def test_default_dark_style_constant_is_valid(self) -> None:
        """The DEFAULT_DARK_STYLE constant is a valid Pygments style."""
        assert is_valid_style(DEFAULT_DARK_STYLE) is True


class TestColourSchemeForStyle:
    """Tests for the _colour_scheme_for_style function."""

    def test_xcode_is_light(self) -> None:
        """The 'xcode' style has a light background and reports 'light'."""
        assert _colour_scheme_for_style("xcode") == "light"

    def test_github_dark_is_dark(self) -> None:
        """The 'github-dark' style has a dark background and reports 'dark'."""
        assert _colour_scheme_for_style("github-dark") == "dark"

    def test_monokai_is_dark(self) -> None:
        """The 'monokai' style has a dark background and reports 'dark'."""
        assert _colour_scheme_for_style("monokai") == "dark"

    def test_default_is_light(self) -> None:
        """The 'default' Pygments style has a light background and reports 'light'."""
        assert _colour_scheme_for_style("default") == "light"

    def test_default_light_style_constant_matches(self) -> None:
        """DEFAULT_LIGHT_STYLE reports 'light'."""
        assert _colour_scheme_for_style(DEFAULT_LIGHT_STYLE) == "light"

    def test_default_dark_style_constant_matches(self) -> None:
        """DEFAULT_DARK_STYLE reports 'dark'."""
        assert _colour_scheme_for_style(DEFAULT_DARK_STYLE) == "dark"


class TestBuildCodeCssColourScheme:
    """Tests that build_code_css injects color-scheme rules correctly."""

    def test_light_section_contains_color_scheme(self) -> None:
        """Light section contains a color-scheme rule on .highlight."""
        css = build_code_css("default", "monokai")
        light_section = css.split("/* Dark mode syntax highlighting")[0]
        assert "color-scheme" in light_section

    def test_light_section_color_scheme_matches_light_style(self) -> None:
        """Light section color-scheme value matches the luminance of the light style."""
        css = build_code_css("xcode", "monokai")  # xcode is light
        light_section = css.split("/* Dark mode syntax highlighting")[0]
        assert ".highlight { color-scheme: light; }" in light_section

    def test_light_section_color_scheme_dark_when_dark_style_used(self) -> None:
        """Light section uses color-scheme: dark when the light style has a dark background."""
        css = build_code_css("github-dark", "xcode")  # github-dark is dark
        light_section = css.split("/* Dark mode syntax highlighting")[0]
        assert ".highlight { color-scheme: dark; }" in light_section

    def test_auto_dark_section_contains_color_scheme(self) -> None:
        """Auto-dark media query section contains a color-scheme rule."""
        css = build_code_css("default", "monokai")
        assert ":root:not([data-theme]) .highlight { color-scheme:" in css

    def test_auto_dark_color_scheme_matches_dark_style(self) -> None:
        """Auto-dark section color-scheme matches the luminance of the dark style."""
        css = build_code_css("default", "xcode")  # xcode is light
        assert ":root:not([data-theme]) .highlight { color-scheme: light; }" in css

    def test_explicit_dark_section_contains_color_scheme(self) -> None:
        """Explicit dark toggle section contains a color-scheme rule on .highlight."""
        css = build_code_css("default", "monokai")
        assert ':root[data-theme="dark"] .highlight { color-scheme:' in css

    def test_explicit_dark_color_scheme_matches_dark_style(self) -> None:
        """Explicit dark section color-scheme matches the luminance of the dark style."""
        css = build_code_css("default", "xcode")  # xcode is light
        assert ':root[data-theme="dark"] .highlight { color-scheme: light; }' in css



    """Tests for the build_code_css function."""

    def test_returns_string(self) -> None:
        """build_code_css returns a non-empty string."""
        css = build_code_css("default", "monokai")
        assert isinstance(css, str)
        assert len(css) > 0

    def test_contains_light_mode_comment(self) -> None:
        """Output contains the light mode comment block."""
        css = build_code_css("default", "monokai")
        assert "/* Light mode syntax highlighting */" in css

    def test_contains_dark_mode_system_comment(self) -> None:
        """Output contains the dark mode system preference comment block."""
        css = build_code_css("default", "monokai")
        assert "/* Dark mode syntax highlighting (system preference) */" in css

    def test_contains_dark_mode_explicit_comment(self) -> None:
        """Output contains the dark mode explicit toggle comment block."""
        css = build_code_css("default", "monokai")
        assert "/* Dark mode syntax highlighting (explicit theme toggle) */" in css

    def test_light_rules_are_plain_highlight_selectors(self) -> None:
        """Light mode rules start with .highlight."""
        css = build_code_css("default", "monokai")
        light_section = css.split("/* Dark mode syntax highlighting")[0]
        highlight_lines = [
            line
            for line in light_section.splitlines()
            if line.strip().startswith(".highlight")
        ]
        assert len(highlight_lines) > 0
        for line in highlight_lines:
            assert not line.startswith(":root"), f"Light rule should not have :root prefix: {line}"

    def test_dark_system_rules_use_media_query(self) -> None:
        """Dark mode system preference rules are wrapped in a media query."""
        css = build_code_css("default", "monokai")
        assert "@media (prefers-color-scheme: dark)" in css

    def test_dark_system_rules_use_not_data_theme_prefix(self) -> None:
        """Dark mode system preference rules use :root:not([data-theme]) prefix."""
        css = build_code_css("default", "monokai")
        assert ":root:not([data-theme]) .highlight" in css

    def test_dark_explicit_rules_use_data_theme_dark_prefix(self) -> None:
        """Dark mode explicit rules use :root[data-theme=\"dark\"] prefix."""
        css = build_code_css("default", "monokai")
        assert ':root[data-theme="dark"] .highlight' in css

    def test_different_styles_produce_different_css(self) -> None:
        """Two different style names produce different CSS output."""
        css_default_monokai = build_code_css("default", "monokai")
        css_friendly_github = build_code_css("friendly", "github-dark")
        assert css_default_monokai != css_friendly_github

    def test_same_style_for_light_and_dark(self) -> None:
        """The same style name can be used for both light and dark mode."""
        css = build_code_css("monokai", "monokai")
        assert isinstance(css, str)
        assert len(css) > 0

    def test_ends_with_newline(self) -> None:
        """Output ends with a newline character."""
        css = build_code_css("default", "monokai")
        assert css.endswith("\n")

    def test_default_constants_produce_valid_css(self) -> None:
        """Using DEFAULT_LIGHT_STYLE and DEFAULT_DARK_STYLE produces valid CSS."""
        css = build_code_css(DEFAULT_LIGHT_STYLE, DEFAULT_DARK_STYLE)
        assert ".highlight" in css
        assert "@media (prefers-color-scheme: dark)" in css


class TestCodeStyleConfigValidation:
    """Tests for light_mode_code_style and dark_mode_code_style in parse_site_config_from_dict."""

    def test_default_values_when_absent(self, tmp_path: Path) -> None:
        """When code style keys are absent, the SiteConfig defaults are used."""
        from blogmore.code_styles import DEFAULT_DARK_STYLE, DEFAULT_LIGHT_STYLE
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        assert kwargs["light_mode_code_style"] == DEFAULT_LIGHT_STYLE
        assert kwargs["dark_mode_code_style"] == DEFAULT_DARK_STYLE

    def test_valid_light_mode_style_accepted(self, tmp_path: Path) -> None:
        """A valid Pygments style name for light_mode_code_style is accepted."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"light_mode_code_style": "friendly"}, tmp_path
        )

        assert errors == []
        assert kwargs["light_mode_code_style"] == "friendly"

    def test_valid_dark_mode_style_accepted(self, tmp_path: Path) -> None:
        """A valid Pygments style name for dark_mode_code_style is accepted."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"dark_mode_code_style": "github-dark"}, tmp_path
        )

        assert errors == []
        assert kwargs["dark_mode_code_style"] == "github-dark"

    def test_invalid_light_mode_style_produces_error_and_uses_default(
        self, tmp_path: Path
    ) -> None:
        """An unrecognised light_mode_code_style produces an error and uses the default."""
        from blogmore.code_styles import DEFAULT_LIGHT_STYLE
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"light_mode_code_style": "not-a-real-style"}, tmp_path
        )

        assert len(errors) == 1
        assert "light_mode_code_style" in errors[0]
        assert kwargs["light_mode_code_style"] == DEFAULT_LIGHT_STYLE

    def test_invalid_dark_mode_style_produces_error_and_uses_default(
        self, tmp_path: Path
    ) -> None:
        """An unrecognised dark_mode_code_style produces an error and uses the default."""
        from blogmore.code_styles import DEFAULT_DARK_STYLE
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"dark_mode_code_style": "made-up-style"}, tmp_path
        )

        assert len(errors) == 1
        assert "dark_mode_code_style" in errors[0]
        assert kwargs["dark_mode_code_style"] == DEFAULT_DARK_STYLE

    def test_non_string_light_mode_style_produces_error(self, tmp_path: Path) -> None:
        """A non-string value for light_mode_code_style produces an error."""
        from blogmore.code_styles import DEFAULT_LIGHT_STYLE
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"light_mode_code_style": 42}, tmp_path
        )

        assert len(errors) == 1
        assert "light_mode_code_style" in errors[0]
        assert kwargs["light_mode_code_style"] == DEFAULT_LIGHT_STYLE

    def test_non_string_dark_mode_style_produces_error(self, tmp_path: Path) -> None:
        """A non-string value for dark_mode_code_style produces an error."""
        from blogmore.code_styles import DEFAULT_DARK_STYLE
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"dark_mode_code_style": True}, tmp_path
        )

        assert len(errors) == 1
        assert "dark_mode_code_style" in errors[0]
        assert kwargs["dark_mode_code_style"] == DEFAULT_DARK_STYLE

    def test_both_styles_set_to_valid_values(self, tmp_path: Path) -> None:
        """Both code style fields can be set to valid Pygments style names."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"light_mode_code_style": "emacs", "dark_mode_code_style": "zenburn"},
            tmp_path,
        )

        assert errors == []
        assert kwargs["light_mode_code_style"] == "emacs"
        assert kwargs["dark_mode_code_style"] == "zenburn"


### test_code_styles.py ends here
