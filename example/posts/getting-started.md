---
title: Getting Started with Static Sites
date: 2024-01-20
tags: [tutorial, webdev]
---

# Getting Started with Static Sites

Static site generators are a great way to build fast, secure websites.

## Why Static Sites?

1. **Fast** - No database queries, just static HTML
2. **Secure** - No server-side code to exploit
3. **Simple** - Easy to deploy and maintain

## How Blogmore Works

Blogmore takes your markdown files and converts them into a beautiful, static website using Jinja2 templates.

### Frontmatter

All post metadata is stored in YAML frontmatter at the top of your markdown files:

```yaml
---
title: My Post Title
date: 2024-01-20
tags: [tag1, tag2]
---
```

That's it! Simple and straightforward.
