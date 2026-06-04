# Writing a Page

In BlogMore, there are two types of content: *posts* and *pages*. Posts are dated entries that appear in your blog's listing, archive, RSS feed, and tag/category indexes. Pages are timeless documents that stand on their own — things like an about page, a contact page, or a projects page.

## Posts vs pages

The key differences are:

| | Posts | Pages |
|---|---|---|
| Appear in blog listing | Yes | No |
| Included in feeds | Yes | No |
| Appear in archive | Yes | No |
| Tagged and categorised | Yes | No |
| Sorted by date | Yes | No |
| Appear in site navigation | No | Yes |

Use a page when you want to publish something that isn't a time-based entry — something that doesn't really "belong" in the stream of posts.

## The pages directory

Pages live in a `pages/` subdirectory inside your [content directory](setting_up_your_blog.md#the-pages-directory):

```
posts/
├── pages/
│   ├── about.md
│   └── projects.md
├── hello-world.md
└── python-tips.md
```

BlogMore detects the `pages/` directory automatically. Any `.md` file you place there will be treated as a page rather than a post.

## Creating a page

A page looks very much like a post. Create a new `.md` file inside `pages/` with frontmatter at the top:

```markdown
---
title: About Me
---

Hi, I'm Dave. I write about Python, open source software, and whatever else
catches my interest.

You can find me on [GitHub](https://github.com/davep) and
[Mastodon](https://fosstodon.org/@davep).
```

## Page frontmatter

Pages support a subset of the frontmatter fields available to posts.

### Required fields

#### `title`

The title of the page. Appears as the page heading and in the browser tab.

```yaml
title: About Me
```

### Optional fields

#### `description`

A short description of the page. Used in `<meta name="description">` and social sharing tags. If not set, BlogMore falls back to the first paragraph of the page's content.

```yaml
description: A little about who I am and what I do.
```

#### `cover`

A URL or path to a cover image, used for Open Graph, Twitter Card, and JSON-LD structured data. If not set, BlogMore falls back to the generated platform icons (if available) or the `site_logo`.

```yaml
cover: /images/about-cover.png
```

#### `author`

The name of the page's author. If not set, BlogMore falls back to the `default_author` set in your [configuration](configuration.md).

```yaml
author: Dave Pearson
```

#### `author_url`

The URL of the page's author. If not set, BlogMore falls back to the `default_author_url` set in your [configuration](configuration.md).

```yaml
author_url: https://davep.org/
```

#### `twitter_creator`

The Twitter/X handle of the page's author. Used in Twitter Card meta tags.

```yaml
twitter_creator: "@davep"
```

#### `twitter_site`

The Twitter/X handle of the site. Used in Twitter Card meta tags.

```yaml
twitter_site: "@my_blog"
```

#### `show_toc`

Whether to show the Table of Contents for this page. If not specified, this defaults to the global [`show_toc`](configuration.md#show_toc) setting in your configuration (which itself defaults to `true`). Set to `false` to hide the Table of Contents on this specific page even if it contains headings, or to `true` to show it.

```yaml
show_toc: false
```

#### `show_toc_inline`

Whether to show the inline/collapsed Table of Contents on narrow screens for this page. If not specified, this defaults to the global [`show_toc_inline`](configuration.md#show_toc_inline) setting in your configuration (which itself defaults to `true`). Set to `false` to hide the inline Table of Contents on narrow displays for this specific page (while still showing the floating sidebar Table of Contents on wider displays, provided `show_toc` is enabled).

```yaml
show_toc_inline: false
```

#### `redirect_from`

A list of URL paths (or a single URL path) that should redirect to this page. Fallback HTML redirection files containing a `<meta http-equiv="refresh" content="0; url=...">` redirect and a canonical link tag will be written at these alias paths during the build process.

If the redirect path ends with a slash or has no extension, it will be treated as a directory and write an `index.html` file inside it. If it has a file extension (e.g. `.html` or `.htm`), it will write that file directly.

Examples:

```yaml
# Redirect from legacy URLs
redirect_from:
  - /old-page/path
  - /old-page/file.html
```

Or a single path:

```yaml
redirect_from: /old-page-slug
```


## The special case of `404.md`

Many hosting services, including GitHub Pages, support a custom 404 page that is shown whenever a visitor tries to access a URL that doesn't exist on your site. BlogMore has built-in support for this.

Create a file named `404.md` inside your `pages/` directory:

```markdown
---
title: Page Not Found
---

Sorry, the page you were looking for does not exist.

[Return to the home page](/)
```

BlogMore generates a `404.html` file in the root of your output directory. The `404` page is intentionally excluded from the site navigation — visitors are not meant to find it by browsing; they land there only when a URL does not match.

When you use `blogmore serve` for local testing, the development server will automatically serve this custom page whenever a resource cannot be found, so you can preview the 404 experience before publishing.

If `404.md` is absent, no `404.html` is generated and the server falls back to its built-in 404 response.
