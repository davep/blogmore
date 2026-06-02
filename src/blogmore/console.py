"""Console output and formatting utilities for blogmore."""

from __future__ import annotations

import sys
import time
from collections.abc import Generator
from contextlib import contextmanager


@contextmanager
def timed_step(label: str) -> Generator[None, None, None]:
    """Time a named generation step and print its wall-clock duration.

    Prints `label` immediately (without a trailing newline) so the elapsed
    time can be appended on the same line once the step finishes.  If the
    step raises an exception a bare newline is emitted before re-raising, so
    subsequent output always starts on a fresh line.

    Args:
        label: Human-readable description of the step, printed as it begins.

    Yields:
        Nothing — the caller performs the work inside the `with` block.
    """
    print(label, end="", flush=True)
    start = time.monotonic()
    try:
        yield
    except BaseException:
        print()  # ensure subsequent output starts on a fresh line
        raise
    elapsed = time.monotonic() - start
    print(f" [{elapsed:.2f}s]")


def print_warning(message: str) -> None:
    """Print a warning message to stderr.

    Args:
        message: The warning message to print.
    """
    print(message, file=sys.stderr)


def print_error(message: str) -> None:
    """Print an error message to stderr.

    Args:
        message: The error message to print.
    """
    print(message, file=sys.stderr)
