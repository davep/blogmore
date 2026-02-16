# Blogmore Test Suite

This directory contains the comprehensive test suite for blogmore, built using pytest.

## Test Structure

- **`conftest.py`**: Shared pytest fixtures and test configuration
- **`test_parser.py`**: Unit tests for the markdown parser and Post/Page classes
- **`test_renderer.py`**: Unit tests for the Jinja2 template renderer
- **`test_feeds.py`**: Unit tests for RSS and Atom feed generation
- **`test_generator.py`**: Unit tests for the site generator
- **`test_main.py`**: Integration tests for the CLI interface
- **`test_integration.py`**: End-to-end integration tests for full workflows
- **`fixtures/`**: Test data including sample markdown posts and pages

## Running Tests

### Run all tests
```bash
make test
```

### Run tests with verbose output
```bash
make test-verbose
```

### Run tests with coverage report
```bash
make test-coverage
```

### Run specific test file
```bash
uv run pytest tests/test_parser.py -v
```

### Run specific test
```bash
uv run pytest tests/test_parser.py::TestPostParser::test_parse_file_simple_post -v
```

## Test Coverage

The test suite achieves **84% code coverage** with 143 tests covering:

- ✅ All parser functionality (Post, Page, PostParser)
- ✅ All renderer functionality (TemplateRenderer)
- ✅ All feed generation (RSS and Atom)
- ✅ All site generation features
- ✅ CLI interface and commands
- ✅ End-to-end workflows

### Coverage by Module

| Module | Coverage |
|--------|----------|
| `parser.py` | 82% |
| `renderer.py` | 95% |
| `feeds.py` | 100% |
| `generator.py` | 85% |
| `__main__.py` | 73% |

## Test Isolation

All tests are designed to be:

- **Isolated**: Each test is independent and doesn't affect others
- **Repeatable**: Tests produce consistent results
- **Fast**: The full suite runs in ~5 seconds
- **Safe**: Tests use temporary directories and don't affect the system

## Fixtures

The `fixtures/` directory contains sample data:

- **`posts/`**: Sample markdown posts with various features
  - Simple posts with frontmatter
  - Draft posts
  - Posts with complex Markdown (code blocks, tables, footnotes)
  - Posts without dates
- **`pages/`**: Sample static pages

## CI Integration

Tests are automatically run on every push and pull request via GitHub Actions (`.github/workflows/tests.yml`):

- ✅ Python 3.12 and 3.13
- ✅ All linters (ruff)
- ✅ Type checking (mypy --strict)
- ✅ Spell checking (codespell)
- ✅ Full test suite with coverage
- ✅ Coverage reporting to Codecov

## Writing New Tests

When adding new features:

1. Add unit tests to the appropriate `test_*.py` file
2. Add integration tests to `test_integration.py` if needed
3. Add fixtures to `fixtures/` if needed
4. Ensure tests are isolated and use fixtures/tmp_path
5. Run `make test` to verify all tests pass
6. Check coverage with `make test-coverage`

## Dependencies

Test dependencies are specified in `pyproject.toml`:

- `pytest>=8.0.0` - Test framework
- `pytest-cov>=6.0.0` - Coverage reporting
- `pytest-mock>=3.14.0` - Mocking support
