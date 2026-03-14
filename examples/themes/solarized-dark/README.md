# Solarized Dark Theme

A theme for BlogMore based on the
[Solarized](https://ethanschoonover.com/solarized/) colour palette by Ethan
Schoonover.

Solarized is a precision colour scheme designed to be easy on the eyes for
long reading sessions.  This theme applies Solarized to *both* light and dark
modes so your blog always stays within the palette regardless of the reader's
OS preference.

## What it looks like

- **Dark mode** — warm base03 (`#002b36`) background with muted base0 text
  (`#839496`) and blue/cyan accent links
- **Light mode** — warm base3 (`#fdf6e3`) background with base00 text
  (`#657b83`) and the same accent colours

Both modes use Solarized accent colours for admonition titles, category
badges, and link states.

## Installation

1. Copy `custom.css` into your blog's `extras/` directory:

```
my-blog/
├── extras/
│   └── custom.css
├── posts/
└── blogmore.yaml
```

2. Add the stylesheet to `blogmore.yaml`:

```yaml
extra_stylesheets:
  - /custom.css
```

3. Build your site:

```bash
blogmore build posts/
```

## Customisation

The CSS file uses only BlogMore's CSS custom properties, so you can further
adjust colours by adding more overrides after the Solarized values.  For
example, to use orange links instead of blue:

```css
/* In your extras/custom.css, append: */
:root {
    --link-color: #cb4b16;
    --dark-link-color: #cb4b16;
}
```

See [docs/theming.md](../../docs/theming.md) for the full variable reference.
