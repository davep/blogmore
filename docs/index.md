# BlogMore

BlogMore is a blog-oriented static site generation engine built in Python. It transforms your Markdown files into a complete, modern blog website with a clean, responsive design.

## What is BlogMore?

BlogMore focuses on simplicity and efficiency in creating blog-focused websites. Write your posts in Markdown with frontmatter metadata, and BlogMore handles the rest—generating a complete static site with post listings, tag pages, category pages, archives, and RSS/Atom feeds.

## Key Features

- **Markdown-based content** - Write all your posts in Markdown with support for code highlighting, tables, footnotes, and GitHub-style admonitions
- **Frontmatter metadata** - Control all post metadata (title, date, tags, category, author) through YAML frontmatter
- **Responsive design** - Clean, modern interface that works beautifully on mobile, tablet, and desktop
- **Jinja2 templating** - Fully customisable templates for complete control over your site's appearance
- **Automatic organisation** - Generates tag pages, category pages, and chronological archives automatically
- **RSS and Atom feeds** - Built-in feed generation for syndication
- **Live preview server** - Local development server with automatic rebuilding on changes
- **GitHub Pages integration** - Simple publishing workflow to GitHub Pages (or any git branch)
- **Configurable** - Extensive configuration options via YAML config files or command-line arguments
- **Sidebar customisation** - Optional logo, custom links, and social media icons
- **SEO optimisation** - Proper meta tags, Open Graph tags, and Twitter Card support

## Installation

BlogMore requires Python 3.12 or later.

### Using uv (recommended)

The fastest and most modern way to install BlogMore is with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install blogmore
```

### Using pipx

You can also install BlogMore using [pipx](https://pipx.pypa.io/):

```bash
pipx install blogmore
```

### From source

To install from source for development:

```bash
git clone https://github.com/davep/blogmore.git
cd blogmore
uv sync
```

## Quick Start

Once installed, creating a blog is straightforward:

Create a directory for your posts:

```bash
mkdir posts
```

Write your first post in `posts/hello.md`:

```markdown
---
title: Hello World
date: 2024-01-15
tags: [welcome, meta]
---

Welcome to my new blog powered by BlogMore!
```

Generate your site:

```bash
blogmore build posts/
```

Preview locally:

```bash
blogmore serve posts/
```

Visit `http://localhost:8000` to see your site.

For a comprehensive walkthrough, see the [Getting Started](getting_started.md) guide.

## Getting Help

- **Issues** - Report bugs or request features on the [GitHub issue tracker](https://github.com/davep/blogmore/issues)
- **Discussions** - Ask questions or share ideas in [GitHub Discussions](https://github.com/davep/blogmore/discussions)
- **Source code** - Browse the code at [github.com/davep/blogmore](https://github.com/davep/blogmore)

## Next Steps

- [Getting Started](getting_started.md) - Detailed walkthrough for creating your blog
- [Command Line](command_line.md) - Complete command-line reference
- [Configuration](configuration.md) - Configuration file options and examples
