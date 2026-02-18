# Getting Started with BlogMore

This guide will walk you through creating your first blog with BlogMore, from initial setup to publishing your site.

## Prerequisites

Ensure you have BlogMore installed. If not, see the [installation instructions](index.md#installation).

## Setting Up Your Blog

### 1. Create Your Content Directory

First, create a directory to hold your blog posts:

```bash
mkdir posts
cd posts
```

You can name this directory anything you like—`posts`, `content`, `blog`, etc. BlogMore will scan it recursively for Markdown files.

### 2. Understanding Directory Structure

BlogMore is flexible about how you organise your posts. Here are some common patterns:

**Flat structure** (all posts in one directory):
```
posts/
  ├── hello-world.md
  ├── python-tips.md
  └── web-development.md
```

**Note:** Files can be date-prefixed (e.g., `2026-02-18-hello-world.md`) and BlogMore will automatically remove the date prefix from the URL slug. The post will still use the `date` field from frontmatter for chronological ordering.

**Organised by date**:
```
posts/
  ├── 2024/
  │   ├── 01/
  │   │   └── hello-world.md
  │   └── 02/
  │       └── python-tips.md
  └── 2025/
      └── 01/
          └── web-development.md
```

**Organised by topic**:
```
posts/
  ├── python/
  │   ├── decorators.md
  │   └── type-hints.md
  └── web/
      ├── css-grid.md
      └── javascript-tips.md
```

All approaches work equally well—BlogMore determines post order by the `date` field in frontmatter, not by directory structure.

## Writing Your First Post

Create a new file `posts/hello-world.md`:

```markdown
---
title: Hello World
date: 2024-01-15
tags: [welcome, blogging]
category: meta
author: Your Name
---

Welcome to my new blog! This is my first post using BlogMore.

## Why I Started This Blog

I wanted a simple, fast, and customisable blogging platform...

## What to Expect

I'll be writing about:

- Python programming
- Web development
- Software engineering practices

Stay tuned for more content!
```

## Understanding Frontmatter

Frontmatter is the YAML section at the top of your Markdown file, enclosed by `---` markers. It contains metadata about your post.

### Required Fields

- **`title`** - The post title (must be present)

### Common Optional Fields

- **`date`** - Publication date in `YYYY-MM-DD` format (posts without dates appear at the end)
- **`tags`** - List of tags (as a YAML list or comma-separated string)
- **`category`** - A single category for the post
- **`author`** - Post author name
- **`draft`** - Set to `true` to mark as a draft (excluded by default)
- **`description`** - Brief description (used for meta tags; falls back to first paragraph)

### SEO and Social Media Fields

- **`cover`** - Cover image URL or path for social media sharing
- **`twitter_creator`** - Author's Twitter handle (e.g., `@username`)
- **`twitter_site`** - Site's Twitter handle
- **`modified`** - Last modification date

### Date Formats

BlogMore accepts several date formats:

```yaml
date: 2024-01-15              # Simple date
date: 2024-01-15 14:30:00     # With time
date: 2024-01-15T14:30:00Z    # ISO format with timezone
```

### Tags Examples

Tags can be written as a YAML list or comma-separated string:

```yaml
# YAML list (recommended)
tags: [python, web, tutorial]

# Comma-separated string
tags: python, web, tutorial

# YAML list (multi-line)
tags:
  - python
  - web
  - tutorial
```

## Markdown Features

BlogMore supports standard Markdown plus several extensions.

### Code Blocks with Syntax Highlighting

Use fenced code blocks with language specifiers:

````markdown
```python
def hello():
    print("Hello, world!")
```
````

### Tables

```markdown
| Feature | Supported |
|---------|-----------|
| Tables  | Yes       |
| Code    | Yes       |
```

### Footnotes

```markdown
Here's a statement with a footnote[^1].

[^1]: This is the footnote content.
```

### GitHub-Style Admonitions

BlogMore supports GitHub-style alert boxes:

```markdown
> [!NOTE]
> Useful information that users should know.

> [!TIP]
> Helpful advice for doing things better.

> [!IMPORTANT]
> Key information users need to know.

> [!WARNING]
> Urgent information needing attention.

> [!CAUTION]
> Advice about risks or negative outcomes.
```

Each admonition type has its own colour and icon.

## Building Your Site

Once you've written some posts, generate your site:

```bash
blogmore build posts/
```

This creates an `output/` directory containing your complete static site. You can customise the output directory with the `-o` flag:

```bash
blogmore build posts/ -o my-site/
```

## Local Testing with the Development Server

The `serve` command starts a local HTTP server and automatically rebuilds your site when files change:

```bash
blogmore serve posts/
```

This will:
1. Build your site to `output/`
2. Start a server on `http://localhost:8000`
3. Watch for changes and automatically rebuild

Open `http://localhost:8000` in your browser to preview your site.

### Serve Options

```bash
# Use a different port
blogmore serve posts/ --port 3000

# Specify output directory
blogmore serve posts/ -o my-site/

# Disable auto-rebuild on changes
blogmore serve posts/ --no-watch

# Serve an existing site without rebuilding
blogmore serve -o output/
```

## Categories vs Tags

Understanding the difference helps you organise content effectively:

- **Categories** - Broad topics or sections of your blog. Each post has zero or one category. Example: `python`, `javascript`, `devops`
- **Tags** - Specific topics that can apply across categories. Posts can have multiple tags. Example: `tutorial`, `beginner`, `advanced`, `testing`

Example:
```yaml
---
title: Python Decorators Tutorial
category: python
tags: [tutorial, beginner, decorators]
---
```

Visitors can view all posts in a category at `/category/python.html` or all posts with a tag at `/tag/tutorial.html`.

## Working with Drafts

Mark posts as drafts while you're still working on them:

```yaml
---
title: Work in Progress
date: 2024-01-20
draft: true
---
```

Drafts are excluded by default. Include them during development:

```bash
blogmore serve posts/ --include-drafts
```

## Publishing to GitHub Pages

Once your site is ready, publish it to GitHub Pages using the `publish` command.

### Prerequisites

1. Your blog must be in a git repository
2. You must have a GitHub repository set up
3. Git must be installed and configured

### Publishing Steps

Ensure your changes are committed:

```bash
git add .
git commit -m "Add new blog posts"
```

Publish to GitHub Pages:

```bash
blogmore publish posts/ --branch gh-pages --remote origin
```

This command will:
- Build your site
- Create or update the `gh-pages` branch
- Copy the generated site to that branch
- Commit and push the changes

### Configuring GitHub Pages

After your first publish, configure GitHub Pages in your repository:

1. Go to your repository on GitHub
2. Click **Settings** → **Pages**
3. Under "Source", select the `gh-pages` branch
4. Click **Save**

Your site will be available at `https://username.github.io/repository-name/` within a few minutes.

For more information, see the [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

### Publishing to Other Branches

You can publish to any branch:

```bash
blogmore publish posts/ --branch main --remote origin
```

## Configuration Files

For projects with many options, create a `blogmore.yaml` configuration file:

```yaml
content_dir: posts
output: output
site_title: "My Blog"
site_subtitle: "Thoughts on code and life"
site_url: "https://username.github.io/blog"
default_author: "Your Name"
posts_per_feed: 30
```

Then simply run:

```bash
blogmore build
blogmore serve
blogmore publish
```

See the [Configuration](configuration.md) guide for all available options.

## Customising Your Site

### Site Metadata

Set your site's title, subtitle, and URL via command-line or config file:

```bash
blogmore build posts/ \
  --site-title "My Blog" \
  --site-subtitle "Thoughts on Technology" \
  --site-url "https://example.com"
```

### Adding a Sidebar Logo and Links

Create a `blogmore.yaml` with sidebar configuration:

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

### Custom Stylesheets

Add your own CSS to override or extend the default styles:

```yaml
extra_stylesheets:
  - https://fonts.googleapis.com/css2?family=Inter
  - /assets/custom.css
```

### Custom Templates

For complete control, copy the default templates and modify them:

```bash
# Copy default templates (from the BlogMore installation)
mkdir my-templates
# Copy from src/blogmore/templates/ in the BlogMore source

# Use your templates
blogmore build posts/ --templates my-templates/
```

## Next Steps

Now that you have a working blog, explore these topics:

- [Command Line Reference](command_line.md) - All available commands and options
- [Configuration Guide](configuration.md) - Detailed configuration file documentation
- Customise templates to match your personal style
- Add custom CSS for typography and colours
- Set up automated publishing with GitHub Actions

Happy blogging!
