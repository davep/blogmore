# Blogmore

A blog-oriented static site generation engine built in Python.

> [!IMPORTANT]
> This project is built almost 100% using GitHub Copilot. Every other Python
> project you will find in my repository is good old human-built code. This
> project is the complete opposite: as much as possible I'm trying to write
> no code at all as an experiment in getting to know how this process works,
> how to recognise such code, and to understand those who use this process
> every day to, in future, better guide them.
>
> If "AI written" is a huge red flag for you I suggest you avoid this
> project; you'll find [plenty of other pure-davep-built projects via my
> profile](https://github.com/davep).

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
blogmore build posts/
```

This will generate your site in the `output/` directory.

### Serve the Site Locally

To serve an existing site:

```bash
blogmore serve -o output/
```

Or generate and serve with auto-reload on changes:

```bash
blogmore serve posts/ -o output/
```

This starts a local HTTP server on port 8000 and watches for changes. Open http://localhost:8000/ in your browser.

Options:
- `-o, --output` - Output directory to serve (default: `output/`)
- `-p, --port` - Port to serve on (default: 8000)
- `--no-watch` - Disable watching for changes

Example:
```bash
blogmore serve posts/ --port 3000 --output my-site/
```

### Custom Options

```bash
blogmore build posts/ \
  --templates my-templates/ \
  --output my-site/ \
  --site-title "My Awesome Blog" \
  --site-subtitle "Thoughts on code and technology" \
  --site-url "https://example.com"
```

### Configuration File

Blogmore supports configuration files to avoid repetitive command-line arguments. Create a `blogmore.yaml` or `blogmore.yml` file in your project directory:

```yaml
# blogmore.yaml
content_dir: posts
output: my-site
templates: my-templates
site_title: "My Awesome Blog"
site_subtitle: "Thoughts on code and technology"
site_url: "https://example.com"
include_drafts: false
clean_first: false
posts_per_feed: 30
default_author: "Your Name"
extra_stylesheets:
  - https://example.com/custom.css
  - /assets/extra.css

# Serve-specific options
port: 3000
no_watch: false
```

#### Using Configuration Files

**Automatic Discovery:**
Blogmore automatically searches for `blogmore.yaml` or `blogmore.yml` in the current directory (`.yaml` takes precedence):

```bash
blogmore build  # Uses blogmore.yaml if found
```

**Specify a Config File:**
Use the `-c` or `--config` flag to specify a custom config file:

```bash
blogmore build --config my-config.yaml
```

**Override Config with CLI:**
Command-line arguments always take precedence over configuration file values:

```bash
# Uses blogmore.yaml but overrides site_title
blogmore build --site-title "Different Title"
```

#### Configuration Options

All command-line options can be configured in the YAML file:

- `content_dir` - Directory containing markdown posts
- `templates` - Custom templates directory
- `output` - Output directory (default: `output/`)
- `site_title` - Site title (default: "My Blog")
- `site_subtitle` - Site subtitle (optional)
- `site_url` - Base URL of the site
- `include_drafts` - Include posts marked as drafts (default: `false`)
- `clean_first` - Remove output directory before generating (default: `false`)
- `posts_per_feed` - Maximum posts in feeds (default: `20`)
- `default_author` - Default author name for posts without author in frontmatter
- `extra_stylesheets` - List of additional stylesheet URLs
- `port` - Port for serve command (default: `8000`)
- `no_watch` - Disable file watching in serve mode (default: `false`)

**Note:** The `--config` option itself cannot be set in a configuration file.

### Commands

**Build** (`build`, `generate`, `gen`)
Generate the static site from markdown posts:
```bash
blogmore build posts/ [options]
```

**Serve** (`serve`, `test`)
Serve the site locally with optional generation and auto-reload:
```bash
blogmore serve [posts/] [options]
```

### Common Options

Available for both `build` and `serve` commands:

- `content_dir` - Directory containing markdown posts (required for `build`, optional for `serve`)
- `-c, --config` - Path to configuration file (default: searches for `blogmore.yaml` or `blogmore.yml`)
- `-t, --templates` - Custom templates directory (default: uses bundled templates)
- `-o, --output` - Output directory (default: `output/`)
- `--site-title` - Site title (default: "My Blog")
- `--site-subtitle` - Site subtitle (optional)
- `--site-url` - Base URL of the site
- `--include-drafts` - Include posts marked as drafts
- `--clean-first` - Remove output directory before generating
- `--posts-per-feed` - Maximum posts in feeds (default: 20)
- `--default-author` - Default author name for posts without author in frontmatter
- `--extra-stylesheet` - Additional stylesheet URL (can be used multiple times)

### Serve-Specific Options

- `-p, --port` - Port to serve on (default: 8000)
- `--no-watch` - Disable watching for changes

## Frontmatter Fields

Required:
- `title` - Post title

Optional:
- `date` - Publication date (YYYY-MM-DD format)
- `category` - Post category (e.g., "python", "webdev")
- `tags` - List of tags or comma-separated string
- `draft` - Set to `true` to mark as draft
- `author` - Author name (uses default_author if not specified)

Example:

```yaml
---
title: My Blog Post
date: 2024-01-15
category: python
tags: [python, webdev, tutorial]
author: Jane Smith
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
make checkall  # Run all checks (lint, format, typecheck, spell, tests)
make lint      # Check linting
make typecheck # Type checking with mypy
make test      # Run test suite
```

### Format Code

```bash
make tidy  # Fix formatting and linting issues
```

## Testing

Blogmore has a comprehensive test suite with 143 tests achieving 84% code coverage.

```bash
make test              # Run all tests
make test-verbose      # Run with verbose output
make test-coverage     # Run with detailed coverage report
```

For more information, see the [tests README](tests/README.md).

## License

GPL-3.0-or-later
