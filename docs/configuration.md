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

#### `with_read_time`

Show estimated reading time on each post. When enabled, BlogMore calculates the approximate time to read each post (based on 200 words per minute) and displays it next to the post date on all post listings and individual post pages.

**Type:** Boolean  
**Default:** `false`

```yaml
with_read_time: true
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

#### `with_advert`

When `true` (the default), a small "Generated with BlogMore vX.Y.Z" line is included in the footer of every page, linking to the BlogMore website. Set this to `false` to suppress the footer line entirely.  This is a **configuration file only** option — it cannot be set on the command line.

**Type:** Boolean  
**Default:** `true`

```yaml
with_advert: false
```

#### `clean_urls`

When `true`, any post whose resolved URL ends with `/index.html` has the `index.html` portion removed so that the URL ends with a trailing slash instead.  For example, if `post_path` is set to `posts/{slug}/index.html`, a post with slug `my-first-post` would normally be referenced as:

```
https://example.com/posts/my-first-post/index.html
```

With `clean_urls: true` every mention of that URL — in the generated HTML, RSS/Atom feeds, sitemap, and canonical `<link>` tags — becomes:

```
https://example.com/posts/my-first-post/
```

The output *file* is still written to `posts/my-first-post/index.html` on disk; only the URLs embedded in the generated site change.

This setting has no effect when `post_path` does not produce paths that end in `index.html`.

This is a **configuration file only** option — it cannot be set on the command line.  Off by default.

**Type:** Boolean  
**Default:** `false`

```yaml
clean_urls: true
```

##### Typical usage

Combine `clean_urls` with a `post_path` that places each post in its own directory:

```yaml
post_path: "posts/{slug}/index.html"
clean_urls: true
```

This gives every post a clean, shareable URL such as `https://example.com/posts/my-first-post/`.

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

# Sidebar configuration
site_logo: /images/logo.png

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
