# Copilot Instructions for BlogMore

## Code Style

- Always write full type hints such that the code passes in mypy's strictest
  mode.
- If you use a library that lacks type hints, search for a type hint library
  to go with it.
- Always generate full Google-style docstrings for all methods, functions,
  classes, etc. Do *not* include type information in the docstrings.
- Docstrings always start on the *same line* as the opening triple quote.
  The closing triple quote is *always* on the line after the final line of
  the docstring *iff* it's more than one line.
- We are using Python 3.12 or later; always favour newer Python features
  that exist in Python 3.12 or later.
- Always use full names for variables, functions and classes; do not use
  abbreviations when something can be written in full.
- Always try and keep individual .py files as small as possible. If there's
  a logical unit of work for some code, place it in a .py file that makes
  for a logical unit and name that file appropriately.

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
