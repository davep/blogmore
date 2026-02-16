# Copilot Instructions for BlogMore

## Code Style

- Always write full type hints such that the code passes in mypy's strictest
  mode.
- If you use a library that lacks type hints, search for a type hint library
  to go with it.
- Always generate full Google-style docstrings for all methods, functions,
  classes, etc. Do *not* include type information in the docstrings.

## Repository tools

- We use `uv` to manage the repository.
- The repository has a comprehensive `Makefile`, make use of it, keep it
  tidy, keep it up to date.
- Always ensure that `uv.lock` is up to date.

## Testing

- When making any changes, always run the tests afterwards to be sure that
  there is no regression in behaviour.
- If changes in functionality require changes in tests, make those changes.
- Do not change tests purely to make them pass, only make changes to tests
  when a change demands it.
- Any new functionality requires associated tests.

[//]: # (copilot-instructions.md ends here)
