# Minimal Monochrome Theme

A grayscale design that removes colour entirely and focuses on typography and
whitespace.  The aim is a clean, distraction-free reading experience that
works equally well in light and dark modes.

## Design choices

- **No colour** — the entire palette is built from black, white, and grays
- **Bold links** — links are differentiated by weight and an underline border
  rather than by colour
- **Admonition titles** are all the same gray, making them less visually
  assertive
- **Code blocks** use only subtle background shading

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

To add a single accent colour (for example, a red for links only):

```css
/* Append to your extras/custom.css */
:root {
    --link-color: #c0392b;
    --link-hover-color: #922b21;
    --dark-link-color: #e74c3c;
    --dark-link-hover-color: #ff6b6b;
}
```

See [docs/theming.md](../../docs/theming.md) for the full variable reference.
