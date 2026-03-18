# BlogMore

![BlogMore](https://raw.githubusercontent.com/davep/blogmore/refs/heads/main/.images/blogmore-social-banner.png)

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

## What is BlogMore?

BlogMore is a blog-oriented static site generation engine built in Python. It
transforms your Markdown files into a complete, modern blog website with a
clean, responsive design—no database, no server-side runtime required.

See [my own blog](https://blog.davep.org/) for an example of a site created
with BlogMore (the site is hosted on GitHub pages, with the repository [over
here](https://github.com/davep/davep.github.com)).

## Key Features

- **Static site generator** — produces plain HTML/CSS/JS that can be hosted
  anywhere
- **Markdown-based content** — write all your posts in Markdown with support
  for code highlighting, tables, and footnotes
- **Frontmatter metadata** — control post metadata (title, date, tags,
  category, author) through YAML frontmatter
- **Jinja2 templating** — fully customisable templates for complete control
  over your site's appearance
- **Client-side search** — optional full-text search across post titles and
  content, running entirely in the browser with no external services
- **Automatic icon generation** — generate favicons and platform-specific
  icons (iOS, Android/Chrome, Windows) from a single source image
- **CSS minification** — optional minification of the generated stylesheet
- **JavaScript minification** — optional minification of generated scripts
- **HTML minification** — optional minification of every generated HTML page
- **Flexible post URL format** — fully configurable post output paths and URLs
  via the `post_path` option; choose date-based paths, per-post directories,
  category-based layouts, and more
- **Optional reading time display** — estimated reading time shown next to the
  post date, based on 200 words per minute
- **GitHub-style admonitions** — alert boxes (note, tip, important, warning,
  caution) rendered from standard `> [!TYPE]` blockquote syntax
- **RSS and Atom feeds** — built-in feed generation for syndication
- **XML sitemap** — optional `sitemap.xml` for search engine indexing
- **SEO optimisation** — meta tags, Open Graph tags, and Twitter Card support
- **Automatic organisation** — tag pages, category pages, and chronological
  archives generated automatically
- **GitHub Pages integration** — one-command publishing to GitHub Pages (or
  any git branch)
- **Live preview server** — local development server with automatic rebuilding
  on file changes
- **YAML configuration file** — keep all your settings in `blogmore.yaml`
  instead of repeating them on the command line

## Installation

BlogMore requires Python 3.12 or later.

### Using uv (recommended)

The fastest and most modern way to install BlogMore is with
[uv](https://github.com/astral-sh/uv):

```bash
uv tool install blogmore
```

If you don't have `uv` installed you can use [uvx.sh](https://uvx.sh) to
perform the installation. For GNU/Linux or macOS or similar:

```sh
curl -LsSf uvx.sh/blogmore/install.sh | sh
```

or on Windows:

```sh
powershell -ExecutionPolicy ByPass -c "irm https://uvx.sh/blogmore/install.ps1 | iex"
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

## Documentation

Full documentation -- including a getting-started guide, day-to-day usage, a
complete configuration reference, and the command-line reference -- is
available at [blogmore.davep.dev](https://blogmore.davep.dev/).

## Getting Help

- **Feature requests, questions and discussion** — [GitHub Discussions](https://github.com/davep/blogmore/discussions)
- **Bug reports** — [GitHub Issues](https://github.com/davep/blogmore/issues)

## Licence

BlogMore is released under the [GPL-3.0-or-later](./LICENSE) licence.

[//]: # (README.md ends here)
