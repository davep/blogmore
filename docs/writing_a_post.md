# Writing a Post

Posts are the heart of a BlogMore blog. Each post is a Markdown file with a small block of metadata at the top called *frontmatter*. This page covers everything you need to know to write, format, and publish a post.

## Your first post

Create a new `.md` file inside your [content directory](setting_up_your_blog.md#the-content-directory). The filename becomes part of the post's URL, so choose something descriptive and lowercase:

```
posts/hello-world.md
```

At its simplest, a post looks like this:

```markdown
---
title: Hello World
date: 2024-01-15
---

Welcome to my new blog! This is my first post.
```

That's all you need to get started. BlogMore will generate a full HTML page from this file, including the page title, date, and all the surrounding navigation.

## Frontmatter

Frontmatter is the block of YAML at the very top of your Markdown file, enclosed between two lines of `---`. It tells BlogMore everything it needs to know about the post.

### Required fields

#### `title`

The title of the post. This appears as the page heading, in the browser tab, and in listings, feeds, and search results.

```yaml
title: My Thoughts on Python 3.12
```

### Optional fields

#### `date`

The publication date of the post. Posts are sorted chronologically by this field, so it's well worth setting. Posts without a date appear after all dated posts.

```yaml
date: 2024-01-15
```

See [Date formats](#date-formats) below for all accepted formats.

#### `tags`

A list of tags for the post. Tags are specific topics that can span across categories. Each tag gets its own page on the site listing all posts with that tag.

```yaml
tags: [python, tutorial, beginner]
```

Tags can be written in several ways — see [Tags formats](#tags-formats) below.

#### `category`

A single broad category for the post. Each category gets its own page listing all posts in it. A post can belong to at most one category.

```yaml
category: python
```

See [Categories and tags](#categories-and-tags) below for guidance on when to use each.

#### `author`

The name of the post's author. If not set, BlogMore falls back to the `default_author` set in your [configuration](configuration.md).

```yaml
author: Dave Pearson
```

#### `draft`

Set to `true` to mark the post as a draft. Draft posts are excluded from the build by default. This is useful for work in progress that you're not ready to publish.

```yaml
draft: true
```

To include drafts during local development, pass `--include-drafts` on the command line or set `include_drafts: true` in your [configuration](configuration.md). See [Building and Publishing](building.md#including-drafts) for more.

#### `description`

A short description of the post. Used for the `<meta name="description">` tag, Open Graph tags, and Twitter Card tags. If not set, BlogMore falls back to the first paragraph of the post's content.

```yaml
description: A gentle introduction to Python decorators with practical examples.
```

#### `cover`

A URL or path to a cover image, used for Open Graph and Twitter Card social sharing previews.

```yaml
cover: /images/my-post-cover.png
```

#### `twitter_creator`

The Twitter/X handle of the post's author. Used in Twitter Card meta tags.

```yaml
twitter_creator: "@davep"
```

#### `twitter_site`

The Twitter/X handle of the site. Used in Twitter Card meta tags.

```yaml
twitter_site: "@my_blog"
```

#### `modified`

The date the post was last modified. Used in the `<meta name="last-modified">` tag. Accepts the same formats as `date`.

```yaml
modified: 2024-06-01
```

#### `invite_comments`

Override the global [`invite_comments`](configuration.md#invite_comments) setting for this post.  Set to `true` to show the comment invitation section on this post even if it is disabled globally, or to `false` to hide it on this post even if it is enabled globally.

```yaml
invite_comments: false
```

#### `invite_comments_to`

Override the email address used in the comment invitation link for this post.  When set, this value is used as a **literal** email address — no template expansion is applied.  This takes precedence over the global [`invite_comments_to`](configuration.md#invite_comments_to) setting.

```yaml
invite_comments_to: "specific-address@example.com"
```

This key only has an effect when the comment invitation feature is enabled (either globally via [`invite_comments`](configuration.md#invite_comments) or via the per-post `invite_comments` front-matter key above).

### Date formats

BlogMore accepts dates in several formats:

```yaml
date: 2024-01-15              # Simple date
date: 2024-01-15 14:30:00     # Date with time
date: 2024-01-15T14:30:00Z    # ISO 8601 with timezone
```

All formats work for both `date` and `modified`.

### Tags formats

Tags can be written in three ways — choose whichever you find most readable:

```yaml
# Inline YAML list (recommended)
tags: [python, web, tutorial]

# Comma-separated string
tags: python, web, tutorial

# Multi-line YAML list
tags:
  - python
  - web
  - tutorial
```

## Categories and tags

Both categories and tags help visitors find related content, but they serve different purposes:

- **Category** — the broad subject area the post belongs to. Think of it as the section of a magazine: `python`, `devops`, `book-reviews`. A post has at most one category.
- **Tags** — specific topics within a post that might cut across categories. Think of them as an index: `tutorial`, `beginner`, `type-hints`, `testing`. A post can have as many tags as you like.

A well-organised post might look like this:

```yaml
---
title: Python Decorators Explained
category: python
tags: [tutorial, intermediate, decorators]
---
```

Visitors can navigate to `/category/python.html` to see all posts in that category, or to `/tag/tutorial.html` to see all posts tagged with `tutorial`.

## Markdown features

BlogMore supports standard Markdown plus several extensions. The following sections cover the most useful ones.

### Basic formatting

Standard Markdown formatting all works as expected:

```markdown
**bold**, *italic*, `inline code`, ~~strikethrough~~

> Blockquote text

- unordered list
- second item

1. ordered list
2. second item

[link text](https://example.com)

![alt text](/path/to/image.png)
```

#### Strikethrough

Wrap text in double tildes (`~~`) to render it with a line through it:

```markdown
This is ~~deleted~~ and this is ~~struck-out text~~ in a sentence.
```

This produces text where the marked words appear with a horizontal line through them, rendered as an HTML `<del>` element. Use it to indicate content that has been removed or is no longer relevant.

### Code blocks with syntax highlighting

Use fenced code blocks with a language identifier for syntax highlighting:

````markdown
```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```
````

A wide range of languages are supported, including `python`, `javascript`, `typescript`, `bash`, `yaml`, `json`, `html`, `css`, `sql`, `rust`, `go`, and many more.

### Tables

```markdown
| Feature       | Supported |
|---------------|-----------|
| Code blocks   | Yes       |
| Tables        | Yes       |
| Footnotes     | Yes       |
| Admonitions   | Yes       |
```

### Footnotes

```markdown
This is a statement that needs a citation.[^1]

[^1]: The source of the citation.
```

The footnote marker becomes a superscript link, and the footnote text is rendered at the bottom of the post.

### Admonitions

BlogMore supports GitHub-style alert boxes, written as blockquotes with a special tag on the first line:

```markdown
> [!NOTE]
> Useful information that readers should know.

> [!TIP]
> A helpful suggestion for doing things better.

> [!IMPORTANT]
> Key information that readers must not miss.

> [!WARNING]
> Urgent information that needs immediate attention.

> [!CAUTION]
> Advice about risks or negative outcomes.
```

Each type is rendered with a distinct colour scheme and icon so that readers can recognise them at a glance.

### Heading IDs and anchor links

Every heading in a post automatically receives an `id` attribute derived from
its text. For example:

```markdown
## Getting Started
```

becomes:

```html
<h2 id="getting-started">Getting Started</h2>
```

This means you can link directly to any section of a post by appending its
fragment to the URL — for example
`https://example.com/2024/01/15/my-post.html#getting-started`.

#### Custom heading IDs

If you need a specific `id` — for example because the auto-generated one is too
long, or because you want a stable `id` that won't change if you reword the
heading — you can set it explicitly by appending `{#your-id}` to the end of the
heading line:

```markdown
### My Great Heading {#custom-id}
```

This produces:

```html
<h3 id="custom-id">My Great Heading</h3>
```

The custom `id` overrides the auto-generated one. Headings without a `{#…}`
suffix keep their auto-generated IDs as usual.

#### Hover anchor links

To make it easy for readers to share a link to a specific section, BlogMore
renders a small **¶** symbol at the end of every heading. The symbol is
invisible by default and appears when the reader moves the mouse over the
heading. Clicking the symbol navigates the browser to that heading's URL
fragment, where the address can be copied from the browser's location bar.

The anchor appears and disappears with a smooth fade and does not affect the
layout of the page in any way.
