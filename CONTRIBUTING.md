# Contributing to BlogMore

Thank you for your interest in contributing! To help keep the project
healthy and maintainable, please follow these guidelines:

## Read First

- **Start by reading the [README](./README.md) and the documentation at
  [blogmore.davep.dev](https://blogmore.davep.dev/).**
- If you plan to use AI tools to contribute, you **must** read and follow
  both [AGENTS.md](./AGENTS.md) and
  [THEME_DEVELOPMENT_GUIDELINES.md](./THEME_DEVELOPMENT_GUIDELINES.md).

## Before Opening a Pull Request

- **For non-trivial changes:**
  1. **Check for existing discussions, issues, and old (including closed)
     PRs** to avoid duplicating work or missing context.
  2. **Start a new discussion** describing your intended change and get
     feedback before you code.
- **Trivial changes** (typos, small doc fixes, etc.) can be submitted
  directly without prior discussion.
- **If you use AI to help with your PR,** clearly state what tool(s) you
  used in your PR description.

## Code Quality and Process

- Follow the code style and architecture described in
  [AGENTS.md](./AGENTS.md).
- Run `make checkall` before submitting to ensure your code passes type
  checks, linting, formatting, spellcheck, and tests.
- Add or update tests for any new or changed functionality.
- Update documentation and `blogmore.yaml.example` if you add or change
  user-facing features or config options.
- Add a `ChangeLog.md` entry for every feature or bugfix PR.
- For changes to CSS, templates, or theming, **read
  THEME_DEVELOPMENT_GUIDELINES.md in full** and follow its rules strictly.

## Submitting Your PR

- Keep commits focused and use imperative commit messages ("Add feature",
  not "Added").
- Be responsive to review feedback and willing to revise your PR.
- If your change is breaking or significant, provide migration notes and
  update docs as needed.

I appreciate your help in making BlogMore better!

[//]: # (CONTRIBUTING.md ends here)
