from pytest import raises

from blogmore.content_path import validate_path_template


class TestValidatePathTemplate:
    def test_valid_template(self):
        """Test that a valid template passes validation."""
        assert validate_path_template("{test}", "tester", {"test"}, "test") is None
        assert (
            validate_path_template("prefix/{test}/suffix", "tester", {"test"}, "test")
            is None
        )
        assert validate_path_template("nothing", "tester", set(), "test") is None
        assert validate_path_template("nothing", "tester", {"test"}, "test") is None

    def test_empty_template(self):
        """Test that an empty template raises a ValueError."""
        with raises(ValueError, match="tester must not be empty"):
            validate_path_template("", "tester", {"test"}, "test")

    def test_unknown_variable(self):
        """Test that a template with an unknown variable raises a ValueError."""
        with raises(
            ValueError, match="tester '.*' contains unknown variable\\(s\\): unknown"
        ):
            validate_path_template("{unknown}", "tester", {"test"}, "test")

    def test_malformed_template(self):
        """Test that a malformed template raises a ValueError."""
        with raises(
            ValueError, match="tester '.*' contains an invalid placeholder: .*"
        ):
            validate_path_template("{test", "tester", {"test"}, "test")
        with raises(
            ValueError, match="tester '.*' contains an invalid placeholder: .*"
        ):
            validate_path_template("test}", "tester", {"test"}, "test")
        with raises(
            ValueError, match="tester '.*' contains an invalid placeholder: .*"
        ):
            validate_path_template("{", "tester", {"test"}, "test")
        with raises(
            ValueError, match="tester '.*' contains an invalid placeholder: .*"
        ):
            validate_path_template("}", "tester", {"test"}, "test")

    def test_missing_required_variable(self):
        """Test that a template missing a required variable raises a ValueError."""
        with raises(
            ValueError,
            match="tester '.*' is missing required variable\\(s\\): {required}",
        ):
            validate_path_template(
                "This is a {test}", "tester", {"test", "required"}, "test", {"required"}
            )

    def test_invalid_required_variable(self):
        """Test that a template with an invalid required variable raises a ValueError."""
        with raises(
            ValueError,
            match="Internal error: required_variables must be a subset of allowed_variables",
        ):
            validate_path_template(
                "This is a {test}", "tester", {"test"}, "test", {"required"}
            )


### test_content_path.py ends here
