# Configuration File Reference

This guide documents all configuration options available in BlogMore configuration files.

## Overview

BlogMore supports YAML configuration files to avoid repetitive command-line arguments. Configuration files make it easier to manage complex setups and maintain consistent settings across multiple commands.

## Configuration File Discovery

BlogMore automatically searches for configuration files in the current directory:

1. `blogmore.yaml` (checked first)
2. `blogmore.yml` (checked second)

If both exist, `blogmore.yaml` takes precedence.

### Specifying a Configuration File

Use the `-c` or `--config` option to specify a custom configuration file:

```bash
blogmore build --config my-config.yaml
```

### Configuration Priority

When both a configuration file and command-line options are present, command-line options always take precedence. This allows you to override specific settings without modifying the configuration file.

Example:
```yaml
# blogmore.yaml
site_title: "My Blog"
output: output
```

```bash
# Override site_title but keep output from config
blogmore build --site-title "Different Title"
```

## Basic Configuration

### Minimal Configuration

At minimum, you typically want to specify the content directory:

```yaml
content_dir: posts
```

### Recommended Configuration

A more complete basic configuration:

```yaml
content_dir: posts
output: public
site_title: "My Blog"
site_subtitle: "Thoughts on code and technology"
site_url: "https://example.com"
default_author: "Your Name"
```

## Configuration Options

### Core Options

#### `content_dir`

Directory containing your Markdown blog posts. BlogMore scans this directory recursively for `.md` files.

**Type:** String (path)  
**Default:** None (required for `build` and `publish`, optional for `serve`)

```yaml
content_dir: posts
```

```yaml
# Can use relative or absolute paths
content_dir: /home/user/blog/posts
```

#### `output`

Directory where the generated static site will be created.

**Type:** String (path)  
**Default:** `output`

```yaml
output: public
```

```yaml
# Use a different output directory
output: build/site
```

#### `templates`

Directory containing custom Jinja2 templates. If not specified, uses BlogMore's bundled default templates.

**Type:** String (path)  
**Default:** None (uses bundled templates)

```yaml
templates: my-templates
```

Custom templates should include:

- `base.html` - Base template
- `index.html` - Homepage listing
- `post.html` - Individual post page
- `archive.html` - Archive page
- `tag.html` - Tag listing page
- `category.html` - Category listing page
- `static/style.css` - Stylesheet

### Site Metadata

#### `site_title`

The title of your blog, displayed in the header and browser title bar.

**Type:** String  
**Default:** `My Blog`

```yaml
site_title: "Dave's Tech Blog"
```

#### `site_subtitle`

An optional subtitle or tagline displayed below the site title.

**Type:** String  
**Default:** Empty string

```yaml
site_subtitle: "Python, web development, and open source"
```

#### `site_description`

A default description for the site, used in `<meta name="description">`, `og:description`, and `twitter:description` tags for pages that do not have a description of their own. This applies to index pages, archive pages, tag pages, category pages, and any post or static page whose content cannot yield an auto-extracted description.

Individual posts and pages that have a `description` field in their frontmatter, or whose content begins with a text paragraph, continue to use that content-specific description — `site_description` is only used as a fallback.

**Type:** String  
**Default:** Empty string (no fallback description)

```yaml
site_description: "A blog about Python, web development, and open source"
```

#### `site_keywords`

Default keywords for the site, used in the `<meta name="keywords">` tag for pages that do not have more specific keywords available.

This applies to index pages, archive pages, tag pages, category pages, tags listing, and categories listing. Individual posts use their own tags as keywords, so `site_keywords` only applies when no post-specific keywords are available. Static pages with no tags also fall back to `site_keywords`.

The value can be specified as either a comma-separated string or a YAML list of strings.

**Type:** String (comma-separated) or list of strings  
**Default:** None (no keywords meta tag)

```yaml
# As a comma-separated string
site_keywords: "blog, technology, programming, python"
```

```yaml
# As a YAML list
site_keywords:
  - blog
  - technology
  - programming
  - python
```

#### `site_url`

The base URL of your site. Used for generating absolute URLs in RSS/Atom feeds, canonical URLs, and Open Graph tags.

**Type:** String (URL)  
**Default:** Empty string

```yaml
site_url: "https://davep.org/blog"
```

**Important:** Include the protocol (`https://`) but no trailing slash.

### Content Options

#### `include_drafts`

Include posts marked with `draft: true` in frontmatter. Useful during development.

**Type:** Boolean  
**Default:** `false`

```yaml
include_drafts: false
```

```yaml
# Include drafts for local testing
include_drafts: true
```

#### `clean_first`

Remove the output directory before generating the site. Ensures no stale files remain from previous builds.

**Type:** Boolean  
**Default:** `false`

```yaml
clean_first: true
```

#### `posts_per_feed`

Maximum number of posts to include in RSS and Atom feeds.

**Type:** Integer  
**Default:** `20`

```yaml
posts_per_feed: 30
```

```yaml
# Include more posts in feeds
posts_per_feed: 50
```

#### `default_author`

Default author name used for posts that don't specify an `author` field in frontmatter.

**Type:** String  
**Default:** None

```yaml
default_author: "Dave Pearson"
```

#### `icon_source`

Filename of the source icon image in the `extras/` directory. BlogMore will generate favicons and platform-specific icons from this image.

**Type:** String  
**Default:** None (auto-detects `icon.png`, `icon.jpg`, `source-icon.png`, `app-icon.png`)

```yaml
icon_source: "icon.png"
```

```yaml
# Use a custom filename
icon_source: "my-logo.png"
```

When a source icon is provided or detected, BlogMore generates 18 icon files optimised for:

- iOS (Apple Touch Icons)
- Android/Chrome (with PWA manifest)
- Windows/Edge (with tile configuration)
- Standard favicons (multi-resolution)

**Requirements:**

- Format: PNG or JPEG
- Size: Square image, ideally 1024×1024 or larger
- Location: Must be in the `extras/` subdirectory of your content directory

See [Metadata and Sidebar — Site icons](metadata_and_sidebar.md#site-icons) for detailed usage instructions.

#### `with_search`

Enable client-side full-text search. When `true`, BlogMore generates a `search_index.json` file containing every post's title, URL, date, and plain-text content, and a `/search.html` page that performs in-browser search as the reader types. A **Search** link is also added to the navigation bar. No external services are required.

**Type:** Boolean  
**Default:** `false`

```yaml
with_search: true
```

When set back to `false` (or omitted), any stale `search.html`, `search_index.json`, and `search.js` files from a previous build that had search enabled are automatically removed.

#### `with_sitemap`

Generate an XML sitemap (`sitemap.xml`) in the root of the output directory. The sitemap conforms to the [Sitemaps protocol](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview) and includes an entry for every HTML page generated for the site, except `search.html`.

**Type:** Boolean  
**Default:** `false`

```yaml
with_sitemap: true
```

A `site_url` should be set when using this option so that sitemap entries contain absolute URLs (e.g. `https://example.com/2024/01/15/my-post.html`). If `site_url` is not provided, URLs will fall back to `https://example.com`.

#### `with_stats`

Generate a blog statistics page. When `true`, BlogMore generates a `/stats.html` page (path configurable via [`stats_path`](#stats_path)) containing posting-pattern histograms, word count and reading-time summaries, blog lifespan, tag and category counts, unique external link count, and a table of the top 20 most-linked external domains. A **Stats** link is automatically added to the navigation bar between **Search** and **RSS**.

**Type:** Boolean  
**Default:** `false`

```yaml
with_stats: true
```

#### `with_calendar`

Generate a calendar view of all posts. When `true`, BlogMore generates a `calendar.html` page (path configurable via [`calendar_path`](#calendar_path)) showing a full year-by-year calendar of the blog's history, from the date of the latest post back to the date of the first post. Days with posts link to the daily archive, months link to the monthly archive, and years link to the yearly archive. A **Calendar** link is automatically added to the navigation bar after **Stats** and before **RSS**.

**Type:** Boolean  
**Default:** `false`

```yaml
with_calendar: true
```

#### `with_read_time`

Show estimated reading time on each post. When enabled, BlogMore calculates the approximate time to read each post (based on the configured words-per-minute rate) and displays it next to the post date on all post listings and individual post pages.

**Type:** Boolean  
**Default:** `false`

```yaml
with_read_time: true
```

#### `read_time_wpm`

Words per minute used when calculating estimated reading time.  Adjust this value to match the expected reading speed of your audience.  Must be a positive integer.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** Integer  
**Default:** `200`

```yaml
read_time_wpm: 250
```

#### `post_path`

Format string that controls the output path (and therefore the URL) of every blog post.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** String  
**Default:** `{year}/{month}/{day}/{slug}.html`

```yaml
post_path: "{year}/{month}/{day}/{slug}.html"
```

##### How it works

The format string uses Python-style `{variable}` placeholders that are substituted with values derived from each post.  The result is joined onto the `output` directory, so the path is always relative to your site root.

##### Available variables

| Variable   | Description                                               | Example value   |
|------------|-----------------------------------------------------------|-----------------|
| `{slug}`   | Post slug (date prefix stripped if present). **Required.**| `my-first-post` |
| `{year}`   | 4-digit year                                              | `2024`          |
| `{month}`  | 2-digit zero-padded month                                 | `01`            |
| `{day}`    | 2-digit zero-padded day                                   | `15`            |
| `{hour}`   | 2-digit zero-padded 24-hour hour                          | `09`            |
| `{minute}` | 2-digit zero-padded minute                                | `30`            |
| `{second}` | 2-digit zero-padded second                                | `05`            |
| `{category}`| Category of the post, slugified for safe URL use         | `python`        |
| `{author}` | Author of the post, slugified for safe URL use            | `dave-pearson`  |

The `{slug}` variable is **required** — every post must produce a unique path, and the slug is the most reliable way to achieve that.

For posts without a date the date/time variables (`{year}`, `{month}`, `{day}`, `{hour}`, `{minute}`, `{second}`) are substituted with empty strings.  Posts with no category or author similarly produce an empty string for those variables.  Consecutive forward slashes that result from empty substitutions are automatically collapsed.

##### Safety

BlogMore always ensures the resolved path remains inside the `output` directory.  A `post_path` value containing `..` segments or other path-traversal constructs is detected and rejected at startup with an error message.

##### Path clash detection

If two or more posts would produce the **same output path** (which can easily happen when using a template that omits date variables), BlogMore prints a prominent `WARNING` before generating the site.  The **newest post** (by date) always wins; older posts that would have overwritten the same file are silently skipped.

```
WARNING: Post path clash detected!  Multiple posts would be written to the same output file.
  Output path : output/post.html
  Winner (newest) : 'My Newer Post'
  Ignored (older): 'My Older Post'
```

Use `clean_first: true` together with a template that guarantees unique paths to avoid unexpected results.

##### Examples

Default layout — year/month/day subdirectories:

```yaml
post_path: "{year}/{month}/{day}/{slug}.html"
```

Every post in its own directory (clean URLs):

```yaml
post_path: "{year}/{month}/{day}/{slug}/index.html"
```

All posts under a single flat `/posts/` directory:

```yaml
post_path: "posts/{slug}.html"
```

Posts organised by category then slug:

```yaml
post_path: "{category}/{slug}.html"
```

Posts organised by author, then year and slug:

```yaml
post_path: "{author}/{year}/{slug}.html"
```

#### `page_path`

Format string that controls the output path (and therefore the URL) of every static page.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** String  
**Default:** `{slug}.html`

```yaml
page_path: "{slug}.html"
```

##### How it works

The format string uses a Python-style `{slug}` placeholder that is substituted with the page's filename stem.  The result is joined onto the `output` directory, so the path is always relative to your site root.  Any intermediate subdirectories are created automatically.

##### Available variables

| Variable | Description                      | Example value |
|----------|----------------------------------|---------------|
| `{slug}` | Page slug derived from filename. **Required.** | `about` |

The `{slug}` variable is the only placeholder available for pages — pages have no date, category, author, or other post-specific metadata.

##### Safety

BlogMore always ensures the resolved path remains inside the `output` directory.  A `page_path` value containing `..` segments or other path-traversal constructs is detected and rejected at startup with an error message.

##### Examples

Default — each page as a flat `.html` file:

```yaml
page_path: "{slug}.html"
```

Each page in its own directory (combine with `clean_urls`):

```yaml
page_path: "{slug}/index.html"
```

All pages under a `/pages/` prefix:

```yaml
page_path: "pages/{slug}.html"
```

Pages in a subdirectory with clean URLs:

```yaml
page_path: "pages/{slug}/index.html"
clean_urls: true
```

#### `with_advert`

When `true` (the default), a small "Generated with BlogMore vX.Y.Z" line is included in the footer of every page, linking to the BlogMore website. Set this to `false` to suppress the footer line entirely.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** Boolean  
**Default:** `true`

```yaml
with_advert: false
```

#### `search_path`

Path (relative to the output directory) where the search page is generated.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** String  
**Default:** `search.html`

```yaml
search_path: "search.html"
```

##### How it works

The path is joined onto the `output` directory.  Any intermediate subdirectories are created automatically, so you can place the search page anywhere under your site root without having to create those directories yourself.

When `clean_urls` is enabled and the path ends in `index.html`, the `index.html` portion is omitted in any URL reference to the search page (navigation links, form action, etc.), so the page is accessible at the clean trailing-slash URL.

> **Note:** The location of the search *data* (`search_index.json`) is not affected by this setting — it is always written to the root of the output directory.

##### Examples

Default — search page at the site root:

```yaml
search_path: "search.html"
```

Search page in its own subdirectory:

```yaml
search_path: "blog/search.html"
```

Search page in its own directory with clean URLs:

```yaml
search_path: "search/index.html"
clean_urls: true
```

This makes the search page accessible at `/search/` rather than `/search/index.html`.

#### `archive_path`

Path (relative to the output directory) where the archive page is generated.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** String  
**Default:** `archive.html`

```yaml
archive_path: "archive.html"
```

##### How it works

The path is joined onto the `output` directory.  Any intermediate subdirectories are created automatically, so you can place the archive page anywhere under your site root without having to create those directories yourself.

The path is always treated as relative to the output directory root — a leading `/` is stripped automatically.  So both `archive/index.html` and `/archive/index.html` produce the same output location.

When `clean_urls` is enabled and the path ends in `index.html`, the `index.html` portion is omitted in any URL reference to the archive page (navigation links, canonical URL, etc.), so the page is accessible at the clean trailing-slash URL.

##### Examples

Default — archive page at the site root:

```yaml
archive_path: "archive.html"
```

Archive page in its own subdirectory:

```yaml
archive_path: "blog/archive.html"
```

Archive page in its own directory with clean URLs:

```yaml
archive_path: "archive/index.html"
clean_urls: true
```

This makes the archive page accessible at `/archive/` rather than `/archive/index.html`.

#### `tags_path`

Path (relative to the output directory) where the tags overview page is generated.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** String  
**Default:** `tags.html`

```yaml
tags_path: "tags.html"
```

##### How it works

The path is joined onto the `output` directory.  Any intermediate subdirectories are created automatically, so you can place the tags page anywhere under your site root without having to create those directories yourself.

The path is always treated as relative to the output directory root — a leading `/` is stripped automatically.  So both `tags/index.html` and `/tags/index.html` produce the same output location.

When `clean_urls` is enabled and the path ends in `index.html`, the `index.html` portion is omitted in any URL reference to the tags page (navigation links, canonical URL, etc.), so the page is accessible at the clean trailing-slash URL.

##### Examples

Default — tags page at the site root:

```yaml
tags_path: "tags.html"
```

Tags page in its own subdirectory:

```yaml
tags_path: "blog/tags.html"
```

Tags page in its own directory with clean URLs:

```yaml
tags_path: "tags/index.html"
clean_urls: true
```

This makes the tags page accessible at `/tags/` rather than `/tags/index.html`.

#### `categories_path`

Path (relative to the output directory) where the categories overview page is generated.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** String  
**Default:** `categories.html`

```yaml
categories_path: "categories.html"
```

##### How it works

The path is joined onto the `output` directory.  Any intermediate subdirectories are created automatically, so you can place the categories page anywhere under your site root without having to create those directories yourself.

The path is always treated as relative to the output directory root — a leading `/` is stripped automatically.  So both `categories/index.html` and `/categories/index.html` produce the same output location.

When `clean_urls` is enabled and the path ends in `index.html`, the `index.html` portion is omitted in any URL reference to the categories page (navigation links, canonical URL, etc.), so the page is accessible at the clean trailing-slash URL.

##### Examples

Default — categories page at the site root:

```yaml
categories_path: "categories.html"
```

Categories page in its own subdirectory:

```yaml
categories_path: "blog/categories.html"
```

Categories page in its own directory with clean URLs:

```yaml
categories_path: "categories/index.html"
clean_urls: true
```

This makes the categories page accessible at `/categories/` rather than `/categories/index.html`.

#### `stats_path`

Path (relative to the output directory) where the blog statistics page is generated.  This is a **configuration file only** option — it cannot be set on the command line.  Only used when [`with_stats`](#with_stats) is `true`.

**Type:** String  
**Default:** `stats.html`

```yaml
stats_path: "stats.html"
```

##### How it works

The path is joined onto the `output` directory.  Any intermediate subdirectories are created automatically.

The path is always treated as relative to the output directory root — a leading `/` is stripped automatically.  So both `stats/index.html` and `/stats/index.html` produce the same output location.

When `clean_urls` is enabled and the path ends in `index.html`, the `index.html` portion is omitted in any URL reference to the stats page (navigation links, canonical URL, etc.), so the page is accessible at the clean trailing-slash URL.

##### Examples

Default — stats page at the site root:

```yaml
stats_path: "stats.html"
```

Stats page in its own subdirectory with clean URLs:

```yaml
stats_path: "stats/index.html"
clean_urls: true
```

This makes the stats page accessible at `/stats/` rather than `/stats/index.html`.

#### `calendar_path`

Path (relative to the output directory) where the calendar page is generated.  This is a **configuration file only** option — it cannot be set on the command line.  Only used when [`with_calendar`](#with_calendar) is `true`.

**Type:** String  
**Default:** `calendar.html`

```yaml
calendar_path: "calendar.html"
```

##### How it works

The path is joined onto the `output` directory.  Any intermediate subdirectories are created automatically.

The path is always treated as relative to the output directory root — a leading `/` is stripped automatically.  So both `calendar/index.html` and `/calendar/index.html` produce the same output location.

When `clean_urls` is enabled and the path ends in `index.html`, the `index.html` portion is omitted in any URL reference to the calendar page (navigation links, canonical URL, etc.), so the page is accessible at the clean trailing-slash URL.

##### Examples

Default — calendar page at the site root:

```yaml
calendar_path: "calendar.html"
```

Calendar page in its own subdirectory with clean URLs:

```yaml
calendar_path: "calendar/index.html"
clean_urls: true
```

This makes the calendar page accessible at `/calendar/` rather than `/calendar/index.html`.

#### `page_1_path`

Output path template for the **first page** of any paginated listing (main index, year/month/day archives, tag pages, and category pages).  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** String  
**Default:** `index.html`

The path is always appended to the end of the section base path being generated.  So for the main index the default produces `output/index.html`, for a year archive it produces `output/2024/index.html`, and for a tag page it produces `output/tag/python/index.html`.

The only available placeholder is `{page}` (the 1-based page number).  It is **not** required for `page_1_path` — the default `index.html` does not use it.

When `clean_urls` is enabled and the resolved path ends in `index.html`, the `index.html` suffix is stripped so the URL uses a trailing slash.

```yaml
page_1_path: "index.html"
```

##### Examples

Default — page 1 is `index.html` within each section directory:

```yaml
page_1_path: "index.html"
```

Include the page number in the first-page filename:

```yaml
page_1_path: "page-{page}.html"
```

#### `page_n_path`

Output path template for **pages 2 and above** of any paginated listing (main index, year/month/day archives, tag pages, and category pages).  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** String  
**Default:** `page/{page}.html`

The path is always appended to the end of the section base path being generated.  So for the main index the default produces `output/page/2.html`, `output/page/3.html`, and so on.

The `{page}` placeholder is **required** and is substituted with the 1-based page number.

When `clean_urls` is enabled and the resolved path ends in `index.html`, the `index.html` suffix is stripped so the URL uses a trailing slash.

```yaml
page_n_path: "page/{page}.html"
```

##### Examples

Default — subsequent pages in a `page/` subdirectory:

```yaml
page_n_path: "page/{page}.html"
```

Flat filenames at the section root:

```yaml
page_n_path: "p{page}.html"
```

#### `clean_urls`

When `true`, any post or page whose resolved URL ends with `/index.html` has the `index.html` portion removed so that the URL ends with a trailing slash instead.  For example, if `post_path` is set to `posts/{slug}/index.html`, a post with slug `my-first-post` would normally be referenced as:

```
https://example.com/posts/my-first-post/index.html
```

With `clean_urls: true` every mention of that URL — in the generated HTML, RSS/Atom feeds, sitemap, and canonical `<link>` tags — becomes:

```
https://example.com/posts/my-first-post/
```

The same applies to pages: if `page_path` is set to `pages/{slug}/index.html`, the page URL becomes `pages/about/` instead of `pages/about/index.html`.  The same transformation is applied to the search page if `search_path` ends in `index.html`, to the archive page if `archive_path` ends in `index.html`, to the tags page if `tags_path` ends in `index.html`, to the categories page if `categories_path` ends in `index.html`, and to paginated listing pages if `page_1_path` ends in `index.html`.

The output *file* is still written to its configured path on disk; only the URLs embedded in the generated site change.

This setting has no effect when neither `post_path`, `page_path`, `search_path`, `archive_path`, `tags_path`, `categories_path`, nor `page_1_path` / `page_n_path` produces paths that end in `index.html`.

This is a **configuration file only** option — it cannot be set on the command line.  Off by default.

**Type:** Boolean  
**Default:** `false`

```yaml
clean_urls: true
```

##### Typical usage

Combine `clean_urls` with a `post_path` and/or `page_path` that places content in its own directory:

```yaml
post_path: "posts/{slug}/index.html"
page_path: "pages/{slug}/index.html"
clean_urls: true
```

This gives every post and page a clean, shareable URL such as `https://example.com/posts/my-first-post/` and `https://example.com/pages/about/`.

### Styling Options

#### `minify_css`

Minify the generated CSS and write it as `styles.min.css` instead of `style.css`. This reduces the size of the stylesheet delivered to visitors.

**Type:** Boolean  
**Default:** `false`

```yaml
minify_css: true
```

#### `minify_js`

Minify the generated JavaScript and write it as `theme.min.js` instead of `theme.js`. If search is enabled, `search.js` is also minified and written as `search.min.js`. The original unminified files are not written when this option is enabled.

**Type:** Boolean  
**Default:** `false`

```yaml
minify_js: true
```

#### `minify_html`

Minify all generated HTML output. When enabled, every `.html` file produced by BlogMore is minified before being saved. Unlike the CSS and JavaScript minification options, the output file name is not changed — only the content is minified.

**Type:** Boolean  
**Default:** `false`

```yaml
minify_html: true
```

#### `light_mode_code_style`

The [Pygments](https://pygments.org/styles/) style name to use for syntax highlighting in light mode. This controls the colour scheme applied to fenced code blocks when the visitor is using a light theme (or has not changed the default theme). BlogMore generates a `code.css` file (or `code.min.css` when `minify_css` is enabled) containing only the CSS rules for the configured styles.

**Type:** String (any valid Pygments style name)  
**Default:** `"xcode"`  
**Configuration file only** — cannot be set on the command line.

```yaml
light_mode_code_style: friendly
```

See the [Pygments style gallery](https://pygments.org/styles/) for all available style names.

#### `dark_mode_code_style`

The [Pygments](https://pygments.org/styles/) style name to use for syntax highlighting in dark mode. This controls the colour scheme applied to fenced code blocks when the visitor is using a dark theme or has toggled the theme to dark. BlogMore generates a `code.css` file (or `code.min.css` when `minify_css` is enabled) containing only the CSS rules for the configured styles.

**Type:** String (any valid Pygments style name)  
**Default:** `"github-dark"`  
**Configuration file only** — cannot be set on the command line.

```yaml
dark_mode_code_style: monokai
```

See the [Pygments style gallery](https://pygments.org/styles/) for all available style names.

#### `extra_stylesheets`

List of additional stylesheets to include. Can be absolute URLs or paths relative to your site root.

**Type:** List of strings (URLs or paths)  
**Default:** None

```yaml
extra_stylesheets:
  - https://fonts.googleapis.com/css2?family=Inter
  - /assets/custom.css
  - /assets/syntax-highlighting.css
```

**Note:** Stylesheets are included in the order specified.

#### `head`

Extra tags to inject into the `<head>` element of every generated page. This is a quick way to add custom `<link>`, `<meta>`, or other head tags without creating or overriding templates.

**Type:** List of single-key mappings (tag name → attribute dict)  
**Default:** Empty list  
**Configuration file only** — cannot be set on the command line.

Each entry is a tag name mapped to a dict of its HTML attributes. All attribute values are converted to strings and always emitted in double quotes.

```yaml
head:
  - link:
      rel: author
      href: /humans.txt
  - meta:
      name: theme-color
      content: "#ffffff"
  - link:
      rel: human-json
      href: /human.json
```

The above configuration produces:

```html
<link rel="author" href="/humans.txt">
<meta name="theme-color" content="#ffffff">
<link rel="human-json" href="/human.json">
```

Tags appear in the order listed and are added to **every** generated page.

!!! tip
    Use `head` for small additions like a `humans.txt` link or a theme-colour
    meta tag.  If you need to make extensive changes to the `<head>` element —
    for example to add complex scripts or conditionally include tags — use
    [template overrides](theming.md) instead.

#### `site_logo`

Path or URL to a logo image displayed in the sidebar.

**Type:** String (URL or path)  
**Default:** None

```yaml
site_logo: /images/logo.png
```

```yaml
# Can use external URLs
site_logo: https://example.com/images/logo.svg
```

### Sidebar Configuration

#### `links`

Custom links displayed in the sidebar. Each link has a `title` and `url`.

**Type:** List of objects with `title` and `url` fields  
**Default:** None

```yaml
links:
  - title: About
    url: /about.html
  - title: Projects
    url: /projects.html
  - title: Contact
    url: /contact.html
```

```yaml
# Can link to external sites
links:
  - title: Main Website
    url: https://example.com
  - title: GitHub
    url: https://github.com/username
```

#### `links_title`

Override the title displayed above the links section in the sidebar. By default the section is labelled "Links".

**Type:** String  
**Default:** `"Links"`

```yaml
links_title: "Elsewhere"
```

Can also be set with the `--links-title` command-line option.

#### `socials`

Social media links displayed in the sidebar as icons. Each entry has a `site` (the social media platform) and `url`.

**Type:** List of objects with `site` and `url` fields  
**Default:** None

```yaml
socials:
  - site: github
    url: https://github.com/davep
  - site: mastodon
    url: https://fosstodon.org/@davep
  - site: twitter
    url: https://twitter.com/username
```

**Supported platforms:** Any Font Awesome brand icon name works (e.g., `github`, `mastodon`, `twitter`, `linkedin`, `youtube`, `facebook`, `instagram`, `bluesky`, `threads`, `lastfm`, `steam`, etc.).

#### `socials_title`

Override the title displayed above the social media icons section in the sidebar. By default the section is labelled "Social".

**Type:** String  
**Default:** `"Social"`

```yaml
socials_title: "Connect"
```

#### `pages`

Control which pages from the `pages/` directory are shown in the sidebar and the order in which they appear.

**Type:** List of strings (page slugs)  
**Default:** None (all pages are shown)  
**Config file only**

By default every page created from the `pages/` directory (except the special `404` page) is automatically linked in the sidebar. If you set `pages` to a list of page slugs, only those pages appear in the sidebar, in the order you specify. Pages not listed are still generated but have no automatic sidebar link.

```yaml
pages:
  - about
  - my-tools
  - colophon
```

If `pages` is omitted entirely, or set to an empty list, all pages are shown (the default behaviour).

### Serve Command Options

Options specific to the `serve` command. These are only used when running `blogmore serve`.

#### `port`

Port number for the local development server.

**Type:** Integer  
**Default:** `8000`

```yaml
port: 3000
```

#### `no_watch`

Disable watching for file changes. The site will be generated once but won't automatically rebuild.

**Type:** Boolean  
**Default:** `false`

```yaml
no_watch: false
```

```yaml
# Disable auto-rebuild
no_watch: true
```

### Publish Command Options

Options specific to the `publish` command. These are only used when running `blogmore publish`.

#### `branch`

Git branch to publish to.

**Type:** String  
**Default:** `gh-pages`

```yaml
branch: gh-pages
```

```yaml
# Publish to main branch instead
branch: main
```

#### `remote`

Git remote to push to.

**Type:** String  
**Default:** `origin`

```yaml
remote: origin
```

```yaml
# Push to a different remote
remote: upstream
```

## Complete Example Configuration

Here's a comprehensive example showing all available options:

```yaml
# Core settings
content_dir: posts
output: public
templates: custom-templates

# Site metadata
site_title: "Dave's Tech Blog"
site_subtitle: "Python, web development, and open source"
site_description: "A blog about Python, web development, and open source software"
site_keywords: "python, web development, open source, programming"
site_url: "https://davep.org/blog"

# Content options
include_drafts: false
clean_first: true
posts_per_feed: 30
default_author: "Dave Pearson"
icon_source: "icon.png"
with_search: true
post_path: "{year}/{month}/{day}/{slug}.html"
with_advert: true

# Styling
minify_css: true
minify_js: true
extra_stylesheets:
  - https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700
  - /assets/custom.css

# Extra head tags (configuration file only)
head:
  - link:
      rel: author
      href: /humans.txt
  - meta:
      name: theme-color
      content: "#ffffff"

# Sidebar configuration
site_logo: /images/logo.png

pages:
  - about
  - colophon

links:
  - title: About
    url: /about.html
  - title: Projects
    url: /projects.html
  - title: Contact
    url: /contact.html

socials:
  - site: github
    url: https://github.com/davep
  - site: mastodon
    url: https://fosstodon.org/@davep
  - site: lastfm
    url: https://www.last.fm/user/davep

# Serve options
port: 8080
no_watch: false

# Publish options
branch: gh-pages
remote: origin
```

## Configuration Profiles

You can maintain multiple configuration files for different purposes:

### Development Configuration

`blogmore-dev.yaml`:
```yaml
content_dir: posts
output: dev-output
site_title: "My Blog [DEV]"
site_url: "http://localhost:8000"
include_drafts: true
port: 8000
```

Usage:
```bash
blogmore serve --config blogmore-dev.yaml
```

### Production Configuration

`blogmore-prod.yaml`:
```yaml
content_dir: posts
output: public
site_title: "My Blog"
site_url: "https://example.com"
include_drafts: false
clean_first: true
branch: gh-pages
```

Usage:
```bash
blogmore publish --config blogmore-prod.yaml
```

## Tips and Best Practices

### Keep Configuration in Version Control

Commit your `blogmore.yaml` to version control so team members or future you can easily build the site with the same settings.

```bash
git add blogmore.yaml
git commit -m "Add BlogMore configuration"
```

### Use Comments

YAML supports comments. Use them to document your configuration choices:

```yaml
# Use a custom port to avoid conflicts with other local servers
port: 3000

# Include more posts in feeds since we publish frequently
posts_per_feed: 50
```

### Test Configuration Changes Locally

Always test configuration changes with `blogmore serve` before publishing:

```bash
# Test locally first
blogmore serve --config new-config.yaml

# If everything looks good, publish
blogmore publish --config new-config.yaml
```

### Override for Testing

Use command-line overrides to test variations without modifying your config file:

```bash
# Test with drafts without changing config
blogmore serve --include-drafts

# Test different site title
blogmore build --site-title "Test Title"
```

## Validation

BlogMore validates configuration files on load and will report errors if:

- Required fields are missing (when running `build` or `publish`)
- File paths don't exist
- Invalid values are provided (e.g., non-integer for `port`)

Error messages include the specific problem and the configuration file location.

## See Also

- [Command Line Reference](command_line.md) - All command-line options
- [Getting Started](setting_up_your_blog.md) - Tutorial for creating your first blog
