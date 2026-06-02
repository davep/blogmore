"""Unit tests for the console module."""

import pytest

from blogmore.console import print_error, print_warning, timed_step


class TestPrintStderr:
    """Test the print_warning and print_error functions."""

    def test_print_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that print_warning prints to stderr.

        Args:
            capsys: The pytest capture fixture.
        """
        print_warning("This is a warning message")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "This is a warning message\n"

    def test_print_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that print_error prints to stderr.

        Args:
            capsys: The pytest capture fixture.
        """
        print_error("This is an error message")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "This is an error message\n"


class TestTimedStep:
    """Test the timed_step context manager."""

    def test_timed_step_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that timed_step prints the label and elapsed time on success.

        Args:
            capsys: The pytest capture fixture.
        """
        with timed_step("Doing a task..."):
            pass

        captured = capsys.readouterr()
        # Out should look like "Doing a task... [0.00s]\n" (or with some elapsed time)
        assert captured.out.startswith("Doing a task... [")
        assert captured.out.endswith("s]\n")
        assert captured.err == ""

    def test_timed_step_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that timed_step prints a newline and re-raises on exception.

        Args:
            capsys: The pytest capture fixture.
        """
        with (
            pytest.raises(ValueError, match="Expected failure"),
            timed_step("Doing a failing task..."),
        ):
            raise ValueError("Expected failure")

        captured = capsys.readouterr()
        # Should have printed the label, followed by a bare newline
        assert captured.out == "Doing a failing task...\n"
        assert captured.err == ""
