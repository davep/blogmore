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
- **Built-in search** - Optional client-side full-text search across post titles and content, enabled with `--with-search`; no external services required
- **Automatic icon generation** - Generate favicons and platform-specific icons from a single source image
  - iOS (Apple Touch Icons)
  - Android/Chrome (with PWA manifest)
  - Windows/Edge (with tile configuration)

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

# Publish-specific options
branch: gh-pages
remote: origin
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
- `branch` - Git branch for publish command (default: `gh-pages`)
- `remote` - Git remote for publish command (default: `origin`)
- `socials_title` - Title for the social media icons section in the sidebar (default: `"Social"`)

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

**Publish** (`publish`)
Build and publish the site to a git branch (e.g., for GitHub Pages):
```bash
blogmore publish posts/ [options]
```

This command:
1. Builds your site to the output directory
2. Checks that you're in a git repository
3. Creates or updates a git branch (default: `gh-pages`)
4. Copies the built site to that branch
5. Commits and pushes the changes

Example for GitHub Pages:
```bash
blogmore publish posts/ --branch gh-pages --remote origin
```

**Note:** The publish command requires git to be installed and available in your PATH.

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

### Publish-Specific Options

- `--branch` - Git branch to publish to (default: `gh-pages`)
- `--remote` - Git remote to push to (default: `origin`)

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

## Icon Generation

Blogmore can automatically generate favicons and platform-specific icons from a single source image. Place a high-resolution square image (ideally 1024×1024 or larger) in your `extras/` directory, and Blogmore will generate all necessary icon formats.

### Generated Icons

From a single source image, Blogmore generates 18 icon files for all major platforms:

- **Favicon files**: Multi-resolution `.ico` and PNG sizes (16×16, 32×32, 96×96)
- **Apple Touch Icons**: Optimized for iOS devices (120×120, 152×152, 167×167, 180×180)
- **Android/Chrome icons**: PWA-ready with web manifest (192×192, 512×512)
- **Windows tiles**: Microsoft Edge and Windows 10+ tiles (70×70, 144×144, 150×150, 310×310, 310×150)

All icons are generated to the `/icons` subdirectory to avoid conflicts with other files.

### Configuration

**Auto-detection** (no configuration needed):
Place one of these files in your `extras/` directory:
- `icon.png` (recommended)
- `icon.jpg` or `icon.jpeg`
- `source-icon.png`
- `app-icon.png`

**Custom filename** via CLI:
```bash
blogmore build content/ --icon-source my-logo.png
```

**Custom filename** via config file:
```yaml
# Icon generation
icon_source: "my-logo.png"
```

### Requirements

- Source image should be square
- Recommended size: 1024×1024 or larger
- Supported formats: PNG, JPEG
- Transparent backgrounds (PNG) work best

## Templates

Blogmore uses Jinja2 templates. The default templates are included, but you can customize them:

- `base.html` - Base template
- `index.html` - Homepage listing (shows full post content)
- `post.html` - Individual post page
- `archive.html` - Archive page
- `tag.html` - Tag page
- `category.html` - Category page
- `search.html` - Search page
- `static/style.css` - Stylesheet

## Search

Search is disabled by default.  To enable it, pass `--with-search` on the
command line or set `with_search: true` in the configuration file.

```bash
blogmore build posts/ --with-search
```

```yaml
# blogmore.yaml
with_search: true
```

### How it works

When the site is built with search enabled, two files are added to the output
directory:

- **`search_index.json`** — A JSON array containing the title, URL, date, and
  plain-text body of every published post.
- **`search.html`** — A search page with a text input that loads
  `search_index.json` and performs an in-browser search as the user types.

A **Search** link is added to the top navigation bar on every page.

No external services or server-side processing are required — everything runs
entirely in the reader's browser.

### Performance

The search index is only fetched when the reader opens the search page; it
does not affect the load time of any other page.  The search itself uses
built-in JavaScript string operations — no extra libraries are downloaded.

### Linking to a pre-filled search

Append a `?q=` query string to the search URL to pre-fill the search input
and immediately show results.  For example:

```
https://example.com/search.html?q=python
```

## Reading Time

Estimated reading time is disabled by default.  To enable it, pass
`--with-read-time` on the command line or set `with_read_time: true` in the
configuration file.

```bash
blogmore build posts/ --with-read-time
```

```yaml
# blogmore.yaml
with_read_time: true
```

When enabled, BlogMore calculates the approximate time to read each post based
on 200 words per minute and displays it next to the post date on the index,
archive, tag, category, and individual post pages.

## HTML Minification

HTML minification is disabled by default.  To enable it, pass `--minify-html`
on the command line or set `minify_html: true` in the configuration file.

```bash
blogmore build posts/ --minify-html
```

```yaml
# blogmore.yaml
minify_html: true
```

When enabled, every `.html` file produced by BlogMore — posts, pages, indexes,
archive pages, tag pages, category pages, the search page, and any other
generated HTML — is minified before being saved.  Unlike the CSS and JavaScript
minification options, the file name is not changed; only the content is minified.

## Markdown Features

Blogmore supports all standard Markdown features plus:

- **Fenced code blocks** with syntax highlighting
- **Tables**
- **Table of contents** generation
- **Footnotes** - Use `[^1]` in text and `[^1]: Footnote text` at the bottom
- **GitHub-style admonitions** - Alert boxes for notes, tips, warnings, etc.
- **Custom heading IDs** - Set a specific `id` on any heading with `{#my-id}`

### Custom Heading IDs

Every heading in a post automatically receives a generated `id` attribute
derived from its text, which makes it possible to link directly to any section
of a post (e.g. `https://example.com/2024/01/01/my-post.html#introduction`).

You can also set a custom `id` for any heading by appending `{#your-id}` to the
heading line:

```markdown
### My Great Heading {#custom-id}
```

This produces:

```html
<h3 id="custom-id">My Great Heading</h3>
```

The custom `id` takes precedence over the auto-generated one.  Headings without
a `{#…}` suffix keep their auto-generated IDs as usual.

#### Heading anchor links

To make it easy for readers to share a link to any section, a small **¶**
symbol appears at the end of every heading when the user's mouse hovers over
it.  Clicking the symbol navigates the browser to that heading's URL fragment.
The symbol is invisible at all other times and does not affect the page layout.

### Admonitions (Alerts)

Blogmore supports GitHub-style admonitions (also known as alerts) to highlight important information. These use the same syntax as GitHub Markdown:

```markdown
> [!NOTE]
> Useful information that users should know, even when skimming content.

> [!TIP]
> Helpful advice for doing things better or more easily.

> [!IMPORTANT]
> Key information users need to know to achieve their goal.

> [!WARNING]
> Urgent info that needs immediate user attention to avoid problems.

> [!CAUTION]
> Advises about risks or negative outcomes of certain actions.
```

Each admonition type has its own color scheme and icon:
- **Note** - Blue with ℹ️ icon
- **Tip** - Green with 💡 icon
- **Important** - Purple with ❗ icon
- **Warning** - Orange with ⚠️ icon
- **Caution** - Red with 🚨 icon

Admonitions support all standard Markdown formatting within them, including **bold**, *italic*, `code`, [links](url), and multiple paragraphs.

Example with formatting:
```markdown
> [!TIP]
> You can use **bold**, *italic*, and `code` formatting.
>
> Multiple paragraphs work too!
```

### Footnotes Example

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
