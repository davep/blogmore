# Theming

BlogMore generates sites with a responsive, light/dark-aware default design.
You can customise every aspect of the appearance — from a quick colour tweak
to a completely different layout — without touching the BlogMore source code.

!!! tip "Looking for template docs?"
    Template customisation (overriding HTML templates) is covered in the
    [Templates](templates.md) reference.  This guide focuses on colour
    schemes, typography, and how the two approaches work together.

## How the styling works

BlogMore embeds two stylesheets in every generated site:

- **`static/style.css`** — the main stylesheet, built around **CSS custom properties** (variables) so that colour schemes can be swapped by changing only those properties.
- **`static/code.css`** — a generated stylesheet containing only the Pygments syntax-highlighting rules for the configured light and dark mode code styles.

A small JavaScript file (`static/theme.js`) reads the user's OS preference and any saved cookie preference, then sets `data-theme="dark"` or `data-theme="light"` on the `<html>` element accordingly.

### Syntax highlighting styles

The code-highlighting colour scheme is generated at build time from [Pygments](https://pygments.org/styles/) and written to `code.css` (or `code.min.css` when `minify_css` is enabled).  Only the two configured styles are included — no other Pygments styles add unnecessary size to the file.

Configure the styles in `blogmore.yaml`:

```yaml
light_mode_code_style: friendly    # light mode; default is "default"
dark_mode_code_style: github-dark  # dark mode; default is "monokai"
```

Any style name shown at [https://pygments.org/styles/](https://pygments.org/styles/) is accepted.  BlogMore validates the name at build time and falls back to the default if an unrecognised name is given.

### Dark mode colour variables

Dark mode colours are declared **once** in `:root` as `--dark-*` variables.
Both the JavaScript-driven `[data-theme="dark"]` selector and the CSS media
query fallback (used when JavaScript is disabled) reference those shared
variables via `var()`.  This means you only need to override the `--dark-*`
variables in your custom stylesheet to change dark mode colours across the
entire site.

## Quick start: change colours with a custom stylesheet

The simplest way to customise a BlogMore site is to add a stylesheet that
overrides CSS custom properties.  No template changes required.

### 1. Create your stylesheet

Place a CSS file in your blog's `extras/` directory:

```
my-blog/
├── extras/
│   └── custom.css    ← your theme file
├── posts/
└── blogmore.yaml
```

### 2. Register it in your configuration

```yaml
# blogmore.yaml
extra_stylesheets:
  - /custom.css
```

Your stylesheet is loaded **after** the built-in one, so any rules you declare
will override the defaults.

### 3. Override variables

```css
/* custom.css — light mode overrides */
:root {
    --link-color: #c0392b;
    --link-hover-color: #96281b;
    --link-visited-color: #922b21;
}
```

For dark mode, override the `--dark-*` palette variables (they are shared by
both the media query fallback and the JavaScript toggle):

```css
/* custom.css — dark mode palette */
:root {
    --dark-bg-color: #0d1117;
    --dark-text-color: #c9d1d9;
    --dark-link-color: #58a6ff;
}
```

## Complete CSS variable reference

### Light mode active values

These variables are the values actually used in rendered pages.  They default
to light mode values.  In dark mode they are automatically set to the
corresponding `--dark-*` values.

| Variable | Default | Description |
|---|---|---|
| `--bg-color` | `#fff` | Page background |
| `--text-color` | `#333` | Primary text |
| `--text-secondary` | `#666` | Secondary text (dates, metadata) |
| `--border-color` | `#eee` | Primary borders |
| `--border-color-light` | `#f0f0f0` | Subtle borders |
| `--link-color` | `#0066cc` | Link colour |
| `--link-hover-color` | `#0052a3` | Link hover state |
| `--link-visited-color` | `#551a8b` | Visited link colour |
| `--hover-color` | `#0066cc` | General hover highlight |
| `--hover-color-dark` | `#0052a3` | Darker hover highlight |
| `--code-bg` | `#f5f5f5` | Inline and block code background |
| `--tag-bg` | `#f0f0f0` | Tag badge background |
| `--tag-hover-bg` | `#e0e0e0` | Tag badge hover background |
| `--category-bg` | `#e8f4f8` | Category badge background |
| `--category-hover-bg` | `#d0e8f2` | Category badge hover background |
| `--category-text` | `#0066cc` | Category badge text |
| `--blockquote-border` | `#ddd` | Blockquote left border |
| `--table-border` | `#ddd` | Table borders |
| `--table-header-bg` | `#f0f0f0` | Table header row background |
| `--table-stripe-bg` | `#fafafa` | Alternating table row background |
| `--admonition-note-title-color` | `#0969da` | Note admonition title |
| `--admonition-tip-title-color` | `#1a7f37` | Tip admonition title |
| `--admonition-important-title-color` | `#8250df` | Important admonition title |
| `--admonition-warning-title-color` | `#9a6700` | Warning admonition title |
| `--admonition-caution-title-color` | `#d1242f` | Caution admonition title |

### Dark mode palette variables

These variables hold the colour values used in dark mode.  Override them to
customise how the site looks when dark mode is active — the change applies
automatically to both the JavaScript toggle and the CSS media query fallback.

| Variable | Default | Description |
|---|---|---|
| `--dark-bg-color` | `#1a1a1a` | Dark mode page background |
| `--dark-text-color` | `#e0e0e0` | Dark mode primary text |
| `--dark-text-secondary` | `#a0a0a0` | Dark mode secondary text |
| `--dark-border-color` | `#333` | Dark mode primary borders |
| `--dark-border-color-light` | `#2a2a2a` | Dark mode subtle borders |
| `--dark-link-color` | `#6eb3ff` | Dark mode link colour |
| `--dark-link-hover-color` | `#8cc5ff` | Dark mode link hover |
| `--dark-link-visited-color` | `#b399ff` | Dark mode visited link |
| `--dark-hover-color` | `#6eb3ff` | Dark mode hover highlight |
| `--dark-hover-color-dark` | `#8cc5ff` | Dark mode darker hover |
| `--dark-code-bg` | `#2a2a2a` | Dark mode code background |
| `--dark-tag-bg` | `#2a2a2a` | Dark mode tag background |
| `--dark-tag-hover-bg` | `#333` | Dark mode tag hover |
| `--dark-category-bg` | `#1a3a4a` | Dark mode category background |
| `--dark-category-hover-bg` | `#2a4a5a` | Dark mode category hover |
| `--dark-category-text` | `#6eb3ff` | Dark mode category text |
| `--dark-blockquote-border` | `#444` | Dark mode blockquote border |
| `--dark-table-border` | `#404040` | Dark mode table borders |
| `--dark-table-header-bg` | `#2a2a2a` | Dark mode table header |
| `--dark-table-stripe-bg` | `#222222` | Dark mode table stripe |
| `--dark-admonition-note-title-color` | `#58a6ff` | Dark note title |
| `--dark-admonition-tip-title-color` | `#3fb950` | Dark tip title |
| `--dark-admonition-important-title-color` | `#a371f7` | Dark important title |
| `--dark-admonition-warning-title-color` | `#d29922` | Dark warning title |
| `--dark-admonition-caution-title-color` | `#f85149` | Dark caution title |

## Example: full colour override

The following stylesheet demonstrates overriding all colour variables.  It
is a good starting point for building your own theme.

```css
/* Light mode palette */
:root {
    --bg-color: #fdfdf7;
    --text-color: #222;
    --text-secondary: #6b6b6b;
    --border-color: #e4e4e0;
    --border-color-light: #edede9;
    --link-color: #c0392b;
    --link-hover-color: #96281b;
    --link-visited-color: #7b241c;
    --hover-color: #c0392b;
    --hover-color-dark: #96281b;
    --code-bg: #f2f2ed;
    --tag-bg: #eef0ed;
    --tag-hover-bg: #dde0dc;
    --category-bg: #fde8e6;
    --category-hover-bg: #fbcac7;
    --category-text: #c0392b;
    --blockquote-border: #e0d0ce;
    --table-border: #e0d0ce;
    --table-header-bg: #f2ede0;
    --table-stripe-bg: #faf9f5;
}

/* Dark mode palette — override --dark-* to change dark mode colours */
:root {
    --dark-bg-color: #1c1512;
    --dark-text-color: #ddd5cc;
    --dark-text-secondary: #9d9590;
    --dark-border-color: #3a3028;
    --dark-border-color-light: #2c2420;
    --dark-link-color: #ff8c85;
    --dark-link-hover-color: #ffada8;
    --dark-link-visited-color: #d4a0cb;
    --dark-hover-color: #ff8c85;
    --dark-hover-color-dark: #ffada8;
    --dark-code-bg: #28201c;
    --dark-tag-bg: #2c2420;
    --dark-tag-hover-bg: #3a3028;
    --dark-category-bg: #3a1e1c;
    --dark-category-hover-bg: #4a2e2c;
    --dark-category-text: #ff8c85;
    --dark-blockquote-border: #5a4040;
    --dark-table-border: #3a3028;
    --dark-table-header-bg: #28201c;
    --dark-table-stripe-bg: #201810;
}
```

## Template customisation

For changes beyond colours — different layouts, additional elements, altered
markup — you can override individual templates.  See the
[Templates](templates.md) reference for full details.

### Quick example: add a custom footer note

Copy `base.html` from the BlogMore source into your templates directory and
edit the `<footer>` block.  You only need to copy the files you intend to
change; BlogMore falls back to the built-in templates for everything else.

```
my-blog/
├── my-templates/
│   └── base.html       ← customised copy
├── posts/
└── blogmore.yaml
```

```yaml
# blogmore.yaml
templates: my-templates
```

### Combining templates and stylesheets

Templates and extra stylesheets work together.  A common pattern is:

- Override `base.html` to add an extra `{% block extra_head %}` section, a
  custom font `<link>`, or a sidebar widget.
- Use a custom stylesheet to adjust colours, spacing, and typography without
  duplicating the entire base layout.

See [Template API](template-api.md) for the full list of context variables and
stable template blocks.

## Example themes

The `examples/themes/` directory contains three ready-to-use themes that
demonstrate different customisation approaches:

| Theme | Approach | Description |
|---|---|---|
| `solarized-dark/` | CSS only | Solarized colour scheme with warm accent tones |
| `minimal-monochrome/` | CSS only | Clean grayscale with strong typographic hierarchy |
| `modern-compact/` | CSS + templates | Tighter layout with custom sidebar and post summary |

Each theme directory contains a `README.md` with installation instructions
and a `custom.css` (and optionally custom templates) ready to copy into your
blog.

## Stability guarantees

All CSS custom properties documented in this guide are part of BlogMore's
**stable public API** for v2.x releases.  Specifically:

- CSS variable names will not be renamed without a major version bump.
- New variables may be added at any time; existing ones will not be removed.
- The `data-theme` attribute values (`"dark"` and `"light"`) will not change.
- Template context variables documented in [Template API](template-api.md)
  will remain stable for all v2.x releases.

Any breaking change will be clearly labelled `BREAKING CHANGE` in
[ChangeLog.md](changelog.md) and will include migration instructions.
