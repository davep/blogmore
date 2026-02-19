# Using BlogMore

This guide covers the day-to-day use of BlogMore after initial setup.

## Writing Posts

### Creating a New Post

Create a new Markdown file in your content directory with frontmatter:

```markdown
---
title: My New Post
date: 2024-01-20
tags: [python, tutorial]
category: programming
---

Your post content goes here...
```

### Post Metadata

Every post requires a `title` field. Other common fields include:

- `date` - Publication date (YYYY-MM-DD format)
- `tags` - List of tags for categorisation
- `category` - A single category
- `author` - Post author name
- `draft` - Mark as draft (excluded by default)

See [Getting Started](getting_started.md#understanding-frontmatter) for complete frontmatter documentation.

## Development Workflow

### Starting the Development Server

Start a local server that automatically rebuilds on changes:

```bash
blogmore serve posts/
```

Visit `http://localhost:8000` to preview your site. The site automatically rebuilds when you save changes to any Markdown file.

### Including Drafts

Work on unpublished posts by marking them as drafts and including them during development:

```yaml
---
title: Work in Progress
draft: true
---
```

```bash
blogmore serve posts/ --include-drafts
```

### Using Different Ports

If port 8000 is in use, specify a different port:

```bash
blogmore serve posts/ --port 3000
```

## Building Your Site

Generate a production-ready static site:

```bash
blogmore build posts/
```

This creates an `output/` directory with your complete site. You can then deploy this directory to any static hosting service.

### Clean Builds

Remove the output directory before building to ensure no stale files:

```bash
blogmore build posts/ --clean-first
```

## Publishing

### Publishing to GitHub Pages

Publish your site directly to GitHub Pages:

```bash
blogmore publish posts/
```

This builds your site and pushes it to the `gh-pages` branch. See [Getting Started - Publishing to GitHub Pages](getting_started.md#publishing-to-github-pages) for setup instructions.

### Publishing to Other Branches

Publish to any git branch:

```bash
blogmore publish posts/ --branch main
```

## Organising Content

### Using Categories

Categories help organise posts into distinct sections:

```yaml
---
title: Python Decorators Explained
category: python
---
```

Visitors can view all posts in a category at `/category/python.html`.

### Using Tags

Tags allow cross-categorisation:

```yaml
---
title: Python Decorators Explained
category: python
tags: [tutorial, intermediate, decorators]
---
```

Tags appear on post pages and visitors can view all posts with a tag at `/tag/tutorial.html`.

## Customisation

### Using Configuration Files

Create a `blogmore.yaml` to avoid repeating command-line options:

```yaml
content_dir: posts
site_title: "My Blog"
site_url: "https://example.com"
default_author: "Your Name"
```

Then use simplified commands:

```bash
blogmore build
blogmore serve
blogmore publish
```

See the [Configuration Guide](configuration.md) for all options.

### Adding Custom Styles

Include additional stylesheets:

```yaml
extra_stylesheets:
  - https://fonts.googleapis.com/css2?family=Inter
  - /assets/custom.css
```

Place `custom.css` in your content directory at `assets/custom.css` and BlogMore will copy it to the output.

### Adding Site Icons

BlogMore can automatically generate favicons and platform-specific icons from a single source image. This creates icons optimised for iOS, Android, Windows, and all modern browsers.

#### Quick Start

Place a square, high-resolution image (ideally 1024×1024 or larger) in your content directory's `extras/` subdirectory:

```bash
posts/
  ├── extras/
  │   └── icon.png
  └── my-first-post.md
```

BlogMore will automatically detect the icon and generate 18 icon files:

- **Favicon files** - Multi-resolution `.ico` and PNG alternatives (16×16, 32×32, 96×96)
- **Apple Touch Icons** - Optimised for iOS devices (120×120, 152×152, 167×167, 180×180)
- **Android/Chrome icons** - PWA-ready with web manifest (192×192, 512×512)
- **Windows tiles** - Microsoft Edge and Windows 10+ tiles (70×70, 144×144, 150×150, 310×310, 310×150)

All generated icons are placed in the `/icons` subdirectory of your output.

#### Using a Custom Icon Filename

If your icon has a different filename, specify it in your configuration:

```yaml
icon_source: "my-logo.png"
```

Or via command line:

```bash
blogmore build posts/ --icon-source my-logo.png
```

#### Supported Source Filenames

BlogMore auto-detects these filenames in the `extras/` directory:

- `icon.png` (recommended)
- `icon.jpg` or `icon.jpeg`
- `source-icon.png`
- `app-icon.png`

#### Requirements

- **Format:** PNG or JPEG
- **Size:** 1024×1024 or larger (square)
- **Transparency:** PNG with transparent backgrounds works best

#### What Gets Generated

When a source icon is detected, BlogMore generates:

```
output/
  └── icons/
      ├── favicon.ico               (16×16, 32×32, 48×48 multi-res)
      ├── favicon-16x16.png
      ├── favicon-32x32.png
      ├── favicon-96x96.png
      ├── apple-touch-icon.png      (180×180)
      ├── apple-touch-icon-120.png  (120×120)
      ├── apple-touch-icon-152.png  (152×152)
      ├── apple-touch-icon-167.png  (167×167)
      ├── apple-touch-icon-precomposed.png
      ├── android-chrome-192x192.png
      ├── android-chrome-512x512.png
      ├── mstile-70x70.png
      ├── mstile-144x144.png
      ├── mstile-150x150.png
      ├── mstile-310x310.png
      ├── mstile-310x150.png
      ├── site.webmanifest          (PWA manifest)
      └── browserconfig.xml         (Windows tile config)
```

The necessary HTML meta tags are automatically added to all pages, but only when the icons exist.

### Customising the Sidebar

Add a logo, custom links, and social media icons:

```yaml
site_logo: /images/logo.png

links:
  - title: About
    url: /about.html
  - title: Projects
    url: /projects.html

socials:
  - site: github
    url: https://github.com/username
  - site: mastodon
    url: https://fosstodon.org/@username
```

## Markdown Features

BlogMore supports standard Markdown plus several extensions.

### Syntax Highlighting

Use fenced code blocks with language specifiers:

````markdown
```python
def greet(name):
    return f"Hello, {name}!"
```
````

### Tables

```markdown
| Feature | Status |
|---------|--------|
| Tables  | ✓      |
| Code    | ✓      |
```

### Admonitions

Create alert boxes for important information:

```markdown
> [!NOTE]
> This is a note with useful information.

> [!WARNING]
> This is a warning about something important.
```

Available types: NOTE, TIP, IMPORTANT, WARNING, CAUTION

### Footnotes

Add footnotes to your posts:

```markdown
This statement needs a citation[^1].

[^1]: Source: Example Reference
```

## Common Tasks

### Changing Site Title

Update via configuration file or command line:

```bash
blogmore build posts/ --site-title "New Title"
```

### Setting Site URL

Important for RSS feeds and canonical URLs:

```bash
blogmore build posts/ --site-url "https://example.com"
```

### Controlling Feed Length

Limit the number of posts in RSS/Atom feeds:

```bash
blogmore build posts/ --posts-per-feed 30
```

### Using Custom Templates

Copy the default templates, customise them, and use them:

```bash
blogmore build posts/ --templates my-templates/
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
blogmore serve posts/ --port 8080
```

### Site Not Updating

Use clean builds to remove stale files:

```bash
blogmore build posts/ --clean-first
```

### Drafts Appearing in Production

Ensure `include_drafts` is not set in your production configuration:

```yaml
# blogmore.yaml
include_drafts: false
```

## Next Steps

- [Command Line Reference](command_line.md) - Complete CLI documentation
- [Configuration Guide](configuration.md) - Detailed configuration options
- [Getting Started](getting_started.md) - Initial setup guide
