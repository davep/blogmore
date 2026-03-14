# Example Themes

This directory contains example themes for BlogMore that demonstrate different
levels of customisation.

| Directory | Approach | Description |
|---|---|---|
| [`solarized-dark/`](solarized-dark/) | CSS only | Warm Solarized colour palette for both light and dark modes |
| [`minimal-monochrome/`](minimal-monochrome/) | CSS only | Clean grayscale design; differentiates links with weight instead of colour |
| [`modern-compact/`](modern-compact/) | CSS + templates | Tighter layout with narrower sidebar, Inter font, and a compact post card |

## How to use an example theme

Each theme directory contains a `README.md` with step-by-step installation
instructions.  In general:

1. Copy the theme's `custom.css` into your blog's `extras/` directory.
2. If the theme includes custom `templates/`, copy those into a templates
   directory of your choosing.
3. Reference both in `blogmore.yaml` (see each theme's README for the exact
   snippet).

## Creating your own theme

The two main approaches are:

- **CSS variables only** — override the `--*` and `--dark-*` custom properties
  in a stylesheet added via `extra_stylesheets`.  No template editing needed.
  See [docs/theming.md](../docs/theming.md) for the full variable reference.

- **CSS + custom templates** — copy individual templates from the BlogMore
  source (`src/blogmore/templates/`) into your own templates directory and
  point BlogMore at it via the `templates` configuration option.  See
  [docs/templates.md](../docs/templates.md) and
  [docs/template-api.md](../docs/template-api.md) for the stable contract.
