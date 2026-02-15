# Blogmore

A blog-oriented static site generation engine built in Python.

## Features

- Write everything in Markdown
- All metadata comes from frontmatter
- Uses Jinja2 for templating
- Simple and clean design
- Automatic tag pages and archive generation

## Installation

### Using uv (recommended)

```bash
uv tool install blogmore
```

### Using pipx

```bash
pipx install blogmore
```

### From source

```bash
git clone https://github.com/davep/blogmore.git
cd blogmore
uv sync
```

## Usage

### Basic Usage

Create a directory with your markdown posts:

```bash
mkdir posts
```

Create a markdown file with frontmatter:

```markdown
---
title: My First Post
date: 2024-01-15
tags: [python, blog]
---

This is my first blog post!
```

Generate your site:

```bash
blogmore posts/
```

This will generate your site in the `output/` directory.

### Serve the Site Locally

To preview your generated site locally:

```bash
blogmore serve
```

This starts a local HTTP server on port 8000. Open http://localhost:8000/ in your browser.

Options:
- `-o, --output` - Output directory to serve (default: `output/`)
- `-p, --port` - Port to serve on (default: 8000)

Example:
```bash
blogmore serve --port 3000 --output my-site/
```

### Custom Options

```bash
blogmore posts/ \
  --templates my-templates/ \
  --output my-site/ \
  --site-title "My Awesome Blog" \
  --site-url "https://example.com"
```

### Command Line Options

- `content_dir` - Directory containing markdown posts (required)
- `-t, --templates` - Templates directory (default: `templates/`)
- `-o, --output` - Output directory (default: `output/`)
- `--site-title` - Site title (default: "My Blog")
- `--site-url` - Base URL of the site
- `--include-drafts` - Include posts marked as drafts

## Frontmatter Fields

Required:
- `title` - Post title

Optional:
- `date` - Publication date (YYYY-MM-DD format)
- `category` - Post category (e.g., "python", "webdev")
- `tags` - List of tags or comma-separated string
- `draft` - Set to `true` to mark as draft

Example:

```yaml
---
title: My Blog Post
date: 2024-01-15
category: python
tags: [python, webdev, tutorial]
draft: false
---
```

### Categories vs Tags

**Categories** allow you to organize posts into distinct sections or "sub-blogs" within your site. Each post can have one category, and visitors can view all posts in a category at `/category/{category-name}.html`.

**Tags** are for cross-categorization and can be applied multiple times per post. They're useful for topics that span multiple categories.

For example, a blog might use categories like "python", "javascript", "devops" to separate major topics, while using tags like "tutorial", "advanced", "beginner" to indicate post type.

## Templates

Blogmore uses Jinja2 templates. The default templates are included, but you can customize them:

- `base.html` - Base template
- `index.html` - Homepage listing (shows full post content)
- `post.html` - Individual post page
- `archive.html` - Archive page
- `tag.html` - Tag page
- `category.html` - Category page
- `static/style.css` - Stylesheet

## Markdown Features

Blogmore supports all standard Markdown features plus:

- **Fenced code blocks** with syntax highlighting
- **Tables**
- **Table of contents** generation
- **Footnotes** - Use `[^1]` in text and `[^1]: Footnote text` at the bottom

Example with footnote:
```markdown
---
title: My Post
---

This is a post with a footnote[^1].

[^1]: This is the footnote content.
```

## Development

### Setup

```bash
make setup
```

### Run Checks

```bash
make checkall  # Run all checks (lint, format, typecheck, spell)
make lint      # Check linting
make typecheck # Type checking with mypy
```

### Format Code

```bash
make tidy  # Fix formatting and linting issues
```

## License

GPL-3.0-or-later