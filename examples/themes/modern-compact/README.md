# Modern Compact Theme

A contemporary design with tighter spacing, a narrower sidebar (220 px vs the
default 280 px), and a warm indigo/purple colour palette.

This theme demonstrates how to combine **CSS overrides** with **custom
templates** for layout-level changes.

## Files

| File | Purpose |
|---|---|
| `custom.css` | Colour palette and compact spacing overrides |
| `templates/base.html` | Narrower sidebar; loads Inter font from Google Fonts |
| `templates/_post_summary.html` | Compact post card with all metadata on one line |

## What it looks like

- **Sidebar** — 220 px wide with Inter headings
- **Post cards** — date, reading time, category, and tags in a single compact
  flex row under the post title
- **Colours** — warm indigo/purple accents on a light gray base in light mode;
  deep navy dark mode

## Installation

1. Copy `custom.css` into your blog's `extras/` directory and the `templates/`
   directory into a directory of your choice:

```
my-blog/
├── extras/
│   └── custom.css
├── my-templates/
│   ├── base.html
│   └── _post_summary.html
├── posts/
└── blogmore.yaml
```

2. Update `blogmore.yaml`:

```yaml
templates: my-templates
extra_stylesheets:
  - /custom.css
```

3. Build your site:

```bash
blogmore build posts/
```

## Customisation

### Change the sidebar width

Edit the `--sidebar-width` variable at the top of `custom.css`:

```css
:root {
    --sidebar-width: 260px;
}
```

### Remove the Google Fonts dependency

If you prefer not to load external fonts, remove or replace the `{% block
extra_head %}` section in `templates/base.html`.  The site will fall back to
the system sans-serif stack.

### Switch to a different accent colour

Override the link and category variables in `custom.css`:

```css
:root {
    --link-color: #c0392b;          /* red accents */
    --dark-link-color: #ff8c85;
    --category-text: #c0392b;
    --dark-category-text: #ff8c85;
}
```

See [docs/theming.md](../../docs/theming.md) for the full variable reference.
