"""Tests for the code_styles module."""

from pathlib import Path

from blogmore.code_styles import (
    DEFAULT_DARK_STYLE,
    DEFAULT_LIGHT_STYLE,
    _colour_scheme_for_style,
    _css_var_name,
    _parse_token_rules,
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


class TestParseTokenRules:
    """Tests for the _parse_token_rules helper."""

    def test_returns_dict(self) -> None:
        """_parse_token_rules returns a dictionary."""
        from blogmore.code_styles import _highlight_rules

        rules = _highlight_rules("default")
        result = _parse_token_rules(rules)
        assert isinstance(result, dict)

    def test_base_highlight_selector_parsed(self) -> None:
        """The base .highlight selector is parsed when it has properties."""
        rules = [".highlight { background: #ffffff; }"]
        result = _parse_token_rules(rules)
        assert ".highlight" in result
        assert result[".highlight"]["background"] == "#ffffff"

    def test_token_selector_parsed(self) -> None:
        """A .highlight .k rule is correctly parsed into selector and properties."""
        rules = [".highlight .k { color: #008000; font-weight: bold }"]
        result = _parse_token_rules(rules)
        assert ".highlight .k" in result
        assert result[".highlight .k"]["color"] == "#008000"
        assert result[".highlight .k"]["font-weight"] == "bold"

    def test_comment_after_rule_ignored(self) -> None:
        """Trailing /* comment */ after a rule is not included in properties."""
        rules = [".highlight .c { color: #177500 } /* Comment */"]
        result = _parse_token_rules(rules)
        assert result[".highlight .c"]["color"] == "#177500"
        assert len(result[".highlight .c"]) == 1

    def test_empty_rule_excluded(self) -> None:
        """A rule with no declarations is not included in the result."""
        result = _parse_token_rules([".highlight .x {  }"])
        assert ".highlight .x" not in result

    def test_unrecognised_line_ignored(self) -> None:
        """Lines that do not match the .highlight pattern are silently ignored."""
        result = _parse_token_rules(["pre { margin: 0; }"])
        assert len(result) == 0


class TestCssVarName:
    """Tests for the _css_var_name helper."""

    def test_base_highlight_selector(self) -> None:
        """Base .highlight selector yields --hl-<property>."""
        assert _css_var_name(".highlight", "background") == "--hl-background"

    def test_token_selector(self) -> None:
        """Token selector .highlight .k yields --hl-k-<property>."""
        assert _css_var_name(".highlight .k", "color") == "--hl-k-color"

    def test_multipart_property(self) -> None:
        """A hyphenated property name is preserved verbatim."""
        assert (
            _css_var_name(".highlight .err", "background-color")
            == "--hl-err-background-color"
        )

    def test_multi_char_token(self) -> None:
        """A multi-character token class yields the expected variable name."""
        assert (
            _css_var_name(".highlight .hll", "background-color")
            == "--hl-hll-background-color"
        )


class TestBuildCodeCssColourScheme:
    """Tests that build_code_css injects color-scheme variables correctly."""

    def test_light_section_contains_color_scheme_variable(self) -> None:
        """The :root block contains a --hl-color-scheme custom property."""
        css = build_code_css("default", "monokai")
        root_block = css.split("/* Dark mode syntax highlighting")[0]
        assert "--hl-color-scheme:" in root_block

    def test_light_section_color_scheme_matches_light_style(self) -> None:
        """--hl-color-scheme is 'light' in :root when the light style has a light background."""
        css = build_code_css("xcode", "monokai")  # xcode is light
        root_block = css.split("/* Dark mode syntax highlighting")[0]
        assert "--hl-color-scheme: light;" in root_block

    def test_light_section_color_scheme_dark_when_dark_style_used(self) -> None:
        """--hl-color-scheme is 'dark' in :root when the light style has a dark background."""
        css = build_code_css("github-dark", "xcode")  # github-dark is dark
        root_block = css.split("/* Dark mode syntax highlighting")[0]
        assert "--hl-color-scheme: dark;" in root_block

    def test_auto_dark_section_contains_color_scheme_variable(self) -> None:
        """The auto-dark media query block overrides --hl-color-scheme."""
        css = build_code_css("default", "monokai")
        media_section = css.split(
            "/* Dark mode syntax highlighting (system preference) */"
        )[1].split("/* Dark mode syntax highlighting (explicit")[0]
        assert "--hl-color-scheme:" in media_section

    def test_auto_dark_color_scheme_matches_dark_style(self) -> None:
        """--hl-color-scheme in the media query matches the dark style's luminance."""
        css = build_code_css("default", "xcode")  # xcode is light
        media_section = css.split(
            "/* Dark mode syntax highlighting (system preference) */"
        )[1].split("/* Dark mode syntax highlighting (explicit")[0]
        assert "--hl-color-scheme: light;" in media_section

    def test_explicit_dark_section_contains_color_scheme_variable(self) -> None:
        """The explicit dark toggle block overrides --hl-color-scheme."""
        css = build_code_css("default", "monokai")
        explicit_section = css.split(
            "/* Dark mode syntax highlighting (explicit theme toggle) */"
        )[1]
        assert "--hl-color-scheme:" in explicit_section

    def test_explicit_dark_color_scheme_matches_dark_style(self) -> None:
        """--hl-color-scheme in the explicit block matches the dark style's luminance."""
        css = build_code_css("default", "xcode")  # xcode is light
        explicit_section = css.split(
            "/* Dark mode syntax highlighting (explicit theme toggle) */"
        )[1]
        assert "--hl-color-scheme: light;" in explicit_section

    def test_highlight_rule_uses_color_scheme_variable(self) -> None:
        """.highlight rule uses var(--hl-color-scheme) instead of a hard-coded value."""
        css = build_code_css("default", "monokai")
        assert ".highlight { color-scheme: var(--hl-color-scheme)" in css

    def test_color_scheme_hard_coded_value_absent(self) -> None:
        """No hard-coded color-scheme: light/dark value appears on .highlight."""
        css = build_code_css("xcode", "github-dark")
        assert ".highlight { color-scheme: light" not in css
        assert ".highlight { color-scheme: dark" not in css


class TestBuildCodeCss:
    """Tests for the structure and correctness of build_code_css output."""

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

    def test_contains_syntax_highlighting_rules_comment(self) -> None:
        """Output contains the syntax highlighting rules comment."""
        css = build_code_css("default", "monokai")
        assert "/* Syntax highlighting rules */" in css

    def test_rules_section_has_plain_highlight_selectors(self) -> None:
        """The rules section contains plain .highlight rules without :root prefix."""
        css = build_code_css("default", "monokai")
        rules_section = css.split("/* Syntax highlighting rules */")[1]
        for line in rules_section.splitlines():
            if line.strip():
                assert line.startswith(
                    ".highlight"
                ), f"Rules section should only have .highlight lines, got: {line}"

    def test_highlight_rules_declared_once(self) -> None:
        """Each .highlight selector appears only once across the entire output."""
        css = build_code_css("xcode", "github-dark")
        rule_lines = [
            line
            for line in css.splitlines()
            if line.startswith(".highlight") and "{" in line
        ]
        selectors = [line.split("{")[0].strip() for line in rule_lines]
        assert len(selectors) == len(
            set(selectors)
        ), "Duplicate .highlight selector declarations found"

    def test_dark_system_uses_media_query(self) -> None:
        """Dark mode system preference rules are wrapped in a media query."""
        css = build_code_css("default", "monokai")
        assert "@media (prefers-color-scheme: dark)" in css

    def test_dark_system_uses_not_data_theme_selector(self) -> None:
        """Dark mode system preference block targets :root:not([data-theme])."""
        css = build_code_css("default", "monokai")
        assert ":root:not([data-theme])" in css

    def test_dark_explicit_uses_data_theme_dark_selector(self) -> None:
        """Dark mode explicit block targets :root[data-theme=\"dark\"]."""
        css = build_code_css("default", "monokai")
        assert ':root[data-theme="dark"]' in css

    def test_dark_mode_vars_not_on_highlight_selectors(self) -> None:
        """The dark mode blocks contain variable declarations, not .highlight rules."""
        css = build_code_css("default", "monokai")
        explicit_section = css.split(
            "/* Dark mode syntax highlighting (explicit theme toggle) */"
        )[1].split("/* Syntax highlighting rules */")[0]
        assert ":root[data-theme=" not in explicit_section.replace(
            ':root[data-theme="dark"] {', ""
        )
        assert ".highlight ." not in explicit_section

    def test_different_styles_produce_different_css(self) -> None:
        """Two different style name pairs produce different CSS output."""
        css_a = build_code_css("default", "monokai")
        css_b = build_code_css("friendly", "github-dark")
        assert css_a != css_b

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

    def test_css_custom_properties_used_in_rules(self) -> None:
        """The syntax highlighting rules use var() for all colour values."""
        css = build_code_css("xcode", "github-dark")
        rules_section = css.split("/* Syntax highlighting rules */")[1]
        for line in rules_section.splitlines():
            if line.strip() and ":" in line and ".highlight" in line:
                assert (
                    "var(--hl-" in line
                ), f"Rule should use CSS custom property var(): {line}"


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
