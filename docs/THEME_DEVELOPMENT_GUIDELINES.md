# Theme Development Guidelines

This document is aimed at **AI agents and contributors** working on the
BlogMore codebase.  It describes the stable public contracts that surround
CSS, templates, and theming infrastructure, and explains the rules to follow
when making changes that touch those areas.

Human users looking to *create* a theme should read [Theming](theming.md) and
[Template API](template-api.md) instead.

## ⚠️ Mandatory rule for AI agents: no breaking changes without explicit human approval

**Breaking changes to the theming system are strictly prohibited unless a
human maintainer has explicitly requested or approved them.**

A breaking change is any change that would require the author of an existing
custom theme (stylesheet or template) to modify their work to maintain the
same visual or functional result.  Examples include:

- Renaming or removing a CSS custom property (e.g. `--bg-color`).
- Renaming or removing a template context variable (e.g. `post.title`).
- Renaming or removing a Jinja2 template block.
- Changing the semantics of an existing CSS class in a way that alters layout
  or visual appearance for custom templates.

**If you are an AI agent and you believe a breaking change is necessary:**

1. **Stop.**  Do not make the change.
2. Describe the proposed change and why it is needed in a comment or message
   to the human maintainer.
3. Proceed only after receiving explicit written approval.

Breaking changes, when approved, must:

- Be introduced only in a new **major** version bump (e.g. v1.x → v2.0).
  A minor version bump (v1.x → v1.(x+1)) is **never** sufficient for a
  breaking change, regardless of how small the change appears.
- Be labelled `BREAKING CHANGE` in `ChangeLog.md` with full migration
  instructions.

Additive changes (new CSS custom properties, new context variables, new
template blocks) are backward-compatible.  They require at most a **minor**
version bump and do not need human pre-approval beyond the normal review
process.

## CSS architecture overview

BlogMore's stylesheet (`src/blogmore/templates/static/style.css`) uses CSS
custom properties (variables) as its theming layer.

### Dark mode implementation

Dark mode colours are defined in **two selectors**, both of which reference
shared palette variables:

```
:root                     — declares --dark-* palette variables (values defined once)
  │
  ├── @media (prefers-color-scheme: dark) :root:not([data-theme])
  │     — fallback for no-JavaScript environments; maps --foo to var(--dark-foo)
  │
  └── :root[data-theme="dark"]
        — used by theme.js; maps --foo to var(--dark-foo)
```

**Rule**: When changing a dark mode colour, change the `--dark-*` variable
value in `:root`.  **Never** change only one of the two selector blocks —
they must always reference the same `--dark-*` palette variables.

### Colour variable naming convention

| Prefix | Scope |
|---|---|
| (none) | Active value used by components; resolves to light or dark depending on current mode |
| `--dark-` | Dark mode palette value; always defined in `:root` |

Example pair:

```css
--bg-color           /* active value — used by body { background: var(--bg-color); } */
--dark-bg-color      /* dark palette value — referenced by both dark mode selectors */
```

### CSS file section structure

The stylesheet is divided into clearly labelled sections:

1. **COLOR VARIABLES** — all custom properties, including `--dark-*` palette
2. **BASE STYLES** — reset, `body`, global typography
3. **LAYOUT COMPONENTS** — `.site-container`, `.sidebar`, `.main-wrapper`
4. **CONTENT STYLING** — links, header, post styles, blockquotes, tables
5. **NAVIGATION & PAGINATION** — `.post-navigation`, `.pagination`
6. **ADMONITIONS & FOOTNOTES** — admonition blocks and footnote styles
7. **THEME TOGGLE** — dark/light mode button
8. **Syntax Highlighting** — Pygments light and dark highlight rules
9. **LISTING PAGES** — tags, categories, archive, search

When adding new CSS, place it in the most appropriate section.

### Stable CSS custom properties

The following properties are part of the public API and **must not be
renamed** in a v1.x release:

**Light/active values:**
`--bg-color`, `--text-color`, `--text-secondary`, `--border-color`,
`--border-color-light`, `--link-color`, `--link-hover-color`,
`--link-visited-color`, `--hover-color`, `--hover-color-dark`, `--code-bg`,
`--tag-bg`, `--tag-hover-bg`, `--category-bg`, `--category-hover-bg`,
`--category-text`, `--blockquote-border`, `--table-border`,
`--table-header-bg`, `--table-stripe-bg`, `--admonition-note-title-color`,
`--admonition-tip-title-color`, `--admonition-important-title-color`,
`--admonition-warning-title-color`, `--admonition-caution-title-color`.

**Dark palette values** (all prefixed `--dark-`):
`--dark-bg-color`, `--dark-text-color`, `--dark-text-secondary`,
`--dark-border-color`, `--dark-border-color-light`, `--dark-link-color`,
`--dark-link-hover-color`, `--dark-link-visited-color`, `--dark-hover-color`,
`--dark-hover-color-dark`, `--dark-code-bg`, `--dark-tag-bg`,
`--dark-tag-hover-bg`, `--dark-category-bg`, `--dark-category-hover-bg`,
`--dark-category-text`, `--dark-blockquote-border`, `--dark-table-border`,
`--dark-table-header-bg`, `--dark-table-stripe-bg`,
`--dark-admonition-note-title-color`, `--dark-admonition-tip-title-color`,
`--dark-admonition-important-title-color`,
`--dark-admonition-warning-title-color`,
`--dark-admonition-caution-title-color`.

## Template contract

### Stable context variables

All variables documented in [Template API](template-api.md) are stable for
v1.x.  Key ones that appear in nearly every template:

- `site_title`, `site_subtitle`, `site_url`
- `all_posts` — full sorted list of `Post` objects
- `pages` — sorted list of `Page` objects
- `prev_page_url`, `next_page_url` — pagination URLs (may be `None`)
- `canonical_url`

### Stable Post attributes

`post.title`, `post.html_content`, `post.date`, `post.url`, `post.slug`,
`post.category`, `post.tags`, `post.description`, `post.reading_time`,
`post.modified_date`, `post.draft`, `post.metadata`.

### Stable template blocks

`base.html` provides these blocks that child templates can safely override:
`title`, `feed_links`, `site_author_meta`, `meta_tags`, `extra_head`,
`content`, `feed_nav_links`.

### Stable CSS classes (used in templates)

`.site-container`, `.sidebar`, `.sidebar-content`, `.sidebar-header`,
`.sidebar-pages`, `.sidebar-section`, `.sidebar-links`, `.sidebar-socials`,
`.main-wrapper`, `.post-header`, `.post-content`, `.post-summary`,
`.post-navigation`, `.pagination`, `.tag-cloud`, `.tags`, `.category-link`,
`.theme-toggle`, `.highlight`.

## Rules for making changes

### When editing style.css

1. **Adding a new colour**: add it as both an active variable (no prefix, with
   a light default) and a `--dark-` palette variable in `:root`.  Then add
   the active variable to both dark mode selectors referencing `var(--dark-*)`.

2. **Changing a colour value**: change only the `--dark-*` value in `:root`
   (dark mode) or the active variable's default (light mode).

3. **Renaming a variable**: this is a **breaking change**.  Label it clearly
   in `ChangeLog.md` with `BREAKING CHANGE`, provide the old and new names,
   and only introduce it in a new **major** version.

4. **Adding new selectors**: place them in the correct section, add comments
   if not self-evident.

### When editing templates

1. Do not remove any variable from the context without labelling the change
   as breaking and following the breaking-change policy (see the mandatory
   rule at the top of this document — this requires a human approval and a
   major version bump).

2. Do not rename template blocks without a breaking-change label.

3. If you add a new context variable, document it in
   [Template API](template-api.md).

4. If you add or rename a CSS class used by a template, update the CSS and
   the class table in [Template API](template-api.md).

### When updating documentation

- Changes to theming behaviour → update [Theming](theming.md).
- Changes to context variables or blocks → update [Template API](template-api.md).
- Breaking changes → add a `BREAKING CHANGE` entry to [ChangeLog](changelog.md).

## Checklist before submitting a PR that touches CSS or templates

- [ ] No existing `--*` CSS variable has been renamed.
- [ ] Dark mode colour values were changed via `--dark-*` variables, not
      by editing only one of the two dark mode selectors.
- [ ] New variables follow the `--name` / `--dark-name` convention.
- [ ] Template context variables removed or renamed are labelled as breaking.
- [ ] [Template API](template-api.md) and [Theming](theming.md) are updated
      if the public API changed.
- [ ] `ChangeLog.md` has an entry for the change.
