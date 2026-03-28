# Agent Instructions for BlogMore

## Codebase architecture

All source lives in `src/blogmore/`. Key modules and their responsibilities:

| Module | Responsibility |
|---|---|
| `__main__.py` / `cli.py` | Entry point; CLI argument parsing |
| `config.py` | Loads and merges `blogmore.yaml` into a runtime config object; `parse_site_config_from_dict` is the single source of truth for YAML→`SiteConfig` field mapping |
| `site_config.py` | `SiteConfig` dataclass — the validated, typed site configuration |
| `generator.py` | Core static site generator; orchestrates all page/feed/asset output |
| `parser.py` | Markdown + frontmatter parser; produces `Post` and `Page` objects |
| `renderer.py` | Jinja2 template rendering |
| `publisher.py` | Git-based publishing (`blogmore publish`) |
| `server.py` | Local dev server with file watching (`blogmore serve`) |
| `sitemap.py` | XML sitemap generation |
| `feeds.py` | RSS and Atom feed generation |
| `search.py` | Client-side search index generation |
| `icons.py` | Favicons and touch icons from a single source image |
| `fontawesome.py` | FontAwesome CSS tree-shaking/optimisation |
| `post_path.py` | Configurable output path resolution for posts |
| `pagination_path.py` | Pagination path resolution for configurable index page output paths |
| `content_path.py` | Shared path-resolution utilities for content output paths (used by page_path and post_path) |
| `clean_url.py` | Clean URL transformation utilities (removes index.html from URLs when enabled) |
| `page_path.py` | Page path resolution for configurable output file paths |
| `utils.py` | Shared utility helpers |

The `markdown/` sub-package (`src/blogmore/markdown/`) groups all custom
Markdown extensions:

| Module | Responsibility |
|---|---|
| `markdown/admonitions.py` | Markdown extension: GitHub-style `> [!TYPE]` admonitions |
| `markdown/external_links.py` | Markdown extension: opens external links in a new tab |
| `markdown/heading_anchors.py` | Markdown extension: hover anchor links on headings |
| `markdown/strikethrough.py` | Markdown extension: `~~strikethrough~~` syntax |

Any new Markdown extensions must be added as a new module inside
`src/blogmore/markdown/` and registered in `parser.py`.

Templates live in `src/blogmore/templates/`; the stylesheet is
`src/blogmore/templates/static/style.css`.

When adding a self-contained unit of new functionality, create a new
appropriately-named module rather than growing an existing large file.

## Code style

- Always write full type hints that pass `mypy` in strict mode.
- If a third-party library lacks type hints, search for a companion type-stub
  package (e.g. `types-*`) before adding `# type: ignore` comments.
- Always generate full Google-style docstrings for every module, class,
  method, and function. Do *not* include type information in docstrings.
- Docstrings always start on the *same line* as the opening triple quote.
  The closing triple quote is *always* on its own line when the docstring
  is more than one line.

  ```python
  # Correct — single line
  def foo() -> None:
      """Do the foo thing."""

  # Correct — multi-line
  def bar(value: int) -> str:
      """Convert value to a string representation.

      Args:
          value: The integer to convert.

      Returns:
          A string representation of the value.
      """

  # Wrong — opening quote on its own line
  def baz() -> None:
      """
      Do the baz thing.
      """
  ```

- Target Python 3.12+. Favour newer language features: `match` statements,
  `X | Y` union syntax, `TypeAlias`, `@override`, `tomllib`, etc.
- Use full, descriptive names for variables, functions, and classes. Do not
  use abbreviations when the full word is readable.
- Keep individual `.py` files small and focused on a single logical concern.

## Code quality

Before opening a PR, all of the following must pass cleanly:

| Command | What it checks |
|---|---|
| `make stricttypecheck` | `mypy --strict` type checking |
| `make lint` | `ruff check` linting |
| `make codestyle` | `ruff format --check` formatting |
| `make spellcheck` | `codespell` spell checking across source and docs |
| `make test` | Full test suite |

Run `make checkall` to execute all five in one step. This is the definitive
pre-PR gate.

To auto-fix lint and formatting issues: `make tidy`.

## Repository tools

- We use `uv` to manage the project. Never edit `pyproject.toml` dependency
  lists by hand — use `uv add <pkg>` and `uv remove <pkg>`.
- Always keep `uv.lock` up to date. After adding or removing a dependency,
  run `uv sync` (or `make ready`) so the lock file is regenerated.
- Run `make ready` to sync the virtual environment after pulling changes.
- Run `make setup` (once, after first clone) to install pre-commit hooks.
- The `Makefile` is the canonical interface for development tasks. Keep it
  tidy and up to date whenever new tooling or tasks are introduced.

## Testing

- Run the test suite after every change: `make test`.
- Any new functionality **must** have associated tests.
- If a change in behaviour makes existing tests incorrect, update those tests.
  Do not change tests purely to make them pass without a genuine reason.
- Do not delete or comment out failing tests; fix the underlying code instead.

## Documentation

The `docs/` directory is built with MkDocs. Key files and their scope:

| File | Covers |
|---|---|
| `docs/index.md` | Feature overview / landing page |
| `docs/getting_started.md` | First-time setup tutorial |
| `docs/setting_up_your_blog.md` | `blogmore init` and site structure |
| `docs/writing_a_post.md` | Writing posts, frontmatter |
| `docs/writing_a_page.md` | Writing static pages |
| `docs/configuration.md` | All `blogmore.yaml` options |
| `docs/command_line.md` | All CLI commands and flags |
| `docs/building.md` | `blogmore build` |
| `docs/metadata_and_sidebar.md` | Sidebar and metadata options |
| `docs/theming.md` | User-facing theming guide |
| `docs/template-api.md` | Stable template context/block API |
| `docs/changelog.md` | Mirrors `ChangeLog.md` |

Rules:

- When adding a significant new feature, update the "Key Features" section
  of `README.md`.
- When adding any user-facing functionality (CLI flag, config option,
  behaviour change), update the appropriate file(s) in `docs/`.
- Whenever you add, remove, or change a configuration option in
  `site_config.py` or `config.py`, you **must** update `blogmore.yaml.example`
  to keep it in sync. Every option a user can set must be documented there.
- Before making any change that touches CSS, templates, or the theming
  system, read `THEME_DEVELOPMENT_GUIDELINES.md` in full. The key rule:
  **breaking changes to CSS variables, template context, or template blocks
  require explicit human approval and a major version bump.**
- We maintain a change log in `ChangeLog.md`. Add an entry for every feature
  addition or bug fix. Follow the existing format and link the PR. If the
  most recent `##` heading has a version number rather than "Unreleased",
  open a new section first:

```md
## Unreleased

**Released: WiP**
```

## Commits and PRs

- Write commit messages in the imperative mood ("Add feature", not "Added
  feature" or "Adding feature").
- Keep commits focused; one logical change per commit is preferred.
- Every PR that adds a feature or fixes a bug must have a corresponding
  `ChangeLog.md` entry that links back to the PR number.
- When adding a new configuration property to the configuration file,
  *ensure* that if the user were to change it while in `serve` mode, that
  the new value, no matter what it is, will be reflected in the
  freshly-generated site.  The mechanics depend on the field's category:

  * **Simple scalar** (`str`, `int`, `bool`, `X | None`): the field is
    auto-discovered via dataclass introspection in
    `parse_site_config_from_dict` (`config.py`).  You only need to add it
    to `SiteConfig` with a default value — **no changes to `config.py` are
    required**.  The reload semantics are handled automatically:

    - When the key is **present** in the YAML, the config value is used
      (a matching CLI flag override, if any, always wins).
    - When the key is **absent** from the YAML and a CLI flag was supplied
      at startup, the CLI value is preserved.
    - When the key is **absent** from the YAML and no CLI flag was supplied,
      the `SiteConfig` class default is restored.

    This applies equally to config-file-only fields and to fields that also
    have a CLI flag equivalent.

  * **Complex field** (list, nested object, path template, etc.): add
    explicit handling inside `parse_site_config_from_dict` in `config.py`,
    following the patterns used for `sidebar_pages`, `head`,
    `extra_stylesheets`, and the path template fields.

[//]: # (AGENTS.md ends here)
