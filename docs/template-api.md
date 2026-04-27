# Template API reference

This page documents the **stable contract** for custom templates in BlogMore.
All items listed here will remain compatible across all v2.x releases unless
explicitly noted otherwise.

For a broader introduction to theming — including CSS variable overrides and
example themes — see [Theming](theming.md).

## Template context variables

Every template receives a *context* dictionary when it is rendered.  The table
below lists all variables that are available in every template.

### Global context (all templates)

| Variable | Type | Description |
|---|---|---|
| `site_title` | `str` | Site name from configuration. |
| `site_subtitle` | `str \| None` | Optional subtitle from configuration. |
| `site_description` | `str \| None` | Site description for meta tags. |
| `site_keywords` | `str \| None` | Site-wide keywords for meta tags. |
| `site_url` | `str` | Base URL of the site (e.g. `https://example.com`). |
| `blogmore_version` | `str` | BlogMore version string (e.g. `1.13.0`). |
| `with_search` | `bool` | `True` when search is enabled. |
| `search_url` | `str` | URL to the search page (respects `search_path` and `clean_urls`). |
| `archive_url` | `str` | URL to the archive page (respects `archive_path` and `clean_urls`). |
| `tags_url` | `str` | URL to the tags overview page (respects `tags_path` and `clean_urls`). |
| `categories_url` | `str` | URL to the categories overview page (respects `categories_path` and `clean_urls`). |
| `with_read_time` | `bool` | `True` when reading time display is enabled. |
| `with_backlinks` | `bool` | `True` when the backlinks feature is enabled. |
| `backlinks_title` | `str` | The heading text for the backlinks section (defaults to `"References & mentions"`). |
| `with_advert` | `bool` | `True` when the "Generated with BlogMore" footer is shown. |
| `default_author` | `str \| None` | Default author name from configuration. |
| `styles_css_url` | `str` | URL to the compiled stylesheet (with cache-bust query string). |
| `code_css_url` | `str` | URL to the generated code-highlighting stylesheet (with cache-bust query string). |
| `search_css_url` | `str` | URL to the search-page stylesheet (with cache-bust query string). |
| `stats_css_url` | `str` | URL to the stats-page stylesheet (with cache-bust query string). |
| `archive_css_url` | `str` | URL to the archive-page stylesheet (with cache-bust query string). |
| `calendar_css_url` | `str` | URL to the calendar-page stylesheet (with cache-bust query string). |
| `tag_cloud_css_url` | `str` | URL to the tag/category-cloud stylesheet (with cache-bust query string). |
| `with_stats` | `bool` | `True` when the statistics page is enabled. |
| `stats_url` | `str` | URL to the statistics page (respects `stats_path` and `clean_urls`). |
| `with_calendar` | `bool` | `True` when the calendar page is enabled. |
| `forward_calendar` | `bool` | `True` when the calendar is in forward (oldest-to-newest) order. |
| `calendar_url` | `str` | URL to the calendar page (respects `calendar_path` and `clean_urls`). |
| `with_graph` | `bool` | `True` when the graph page is enabled. |
| `graph_url` | `str` | URL to the graph page (respects `graph_path` and `clean_urls`). |
| `graph_css_url` | `str` | URL to the graph-page stylesheet (with cache-bust query string). |
| `theme_js_url` | `str` | URL to `theme.js` (with cache-bust query string). |
| `search_js_url` | `str` | URL to `search.js` (with cache-bust query string). |
| `favicon_url` | `str \| None` | URL to the site favicon, if one exists. |
| `has_platform_icons` | `bool` | `True` when generated platform icons are present. |
| `fontawesome_css_url` | `str \| None` | Font Awesome CSS URL, when social icons are used. |
| `extra_stylesheets` | `list[str]` | List of extra stylesheet URLs from configuration. |
| `tag_dir` | `str` | URL prefix for tag pages (e.g. `/tags`). |
| `category_dir` | `str` | URL prefix for category pages (e.g. `/categories`). |

#### Sidebar context

These variables are only present when the corresponding configuration keys are
set in `blogmore.yaml`:

| Variable | Type | Description |
|---|---|---|
| `site_logo` | `str` | Path to the site logo image. |
| `links` | `list[LinkEntry]` | Sidebar link entries (`title`, `url`). |
| `links_title` | `str` | Heading for the links section (default `"Links"`). |
| `socials` | `list[SocialEntry]` | Social profile entries (`site`, `url`). |
| `socials_title` | `str` | Heading for the socials section (default `"Social"`). |

#### Pagination context

These variables are present on paginated templates (`index.html`,
`tag.html`, `category.html`, `archive.html`):

| Variable | Type | Description |
|---|---|---|
| `prev_page_url` | `str \| None` | URL of the previous page, or `None`. |
| `next_page_url` | `str \| None` | URL of the next page, or `None`. |
| `canonical_url` | `str \| None` | Canonical URL for this page. |
| `pagination_page_urls` | `list[str]` | Ordered list of all page URLs for this paginated section (index 0 = page 1). Used by the `_pagination.html` macro. |

`pagination_page_urls` is the primary way templates link between pages.  It is
pre-computed by the generator from the `page_1_path` and `page_n_path`
configuration options and respects the `clean_urls` setting.

#### Global context — pagination helpers

Available in every template (including post pages, static pages, etc.):

| Variable | Type | Description |
|---|---|---|
| `pagination_page1_suffix` | `str` | Resolved suffix for a paginated section's first page (e.g. `index.html`, or `""` with `clean_urls`). Used in templates to build links to tag and category first pages. |

This variable lets templates construct tag and category listing URLs without
hard-coding the pagination scheme.  For example:

```jinja2
<a href="/{{ tag_dir }}/{{ safe_tag }}/{{ pagination_page1_suffix }}">{{ tag }}</a>
```

With the default `page_1_path: index.html` this produces `/tag/python/index.html`,
or `/tag/python/` when `clean_urls` is enabled.

### Template-specific context

| Template | Extra variables |
|---|---|
| `index.html` | `all_posts` (full post list), `pages` (static pages list), `prev_page_url`, `next_page_url`, `canonical_url`, `pagination_page_urls` |
| `post.html` | `all_posts`, `pages`, `prev_post` (`Post \| None`), `next_post` (`Post \| None`), `canonical_url`, `backlinks` (list of `Backlink`), `invite_comments_mailto` (`str \| None`) |
| `page.html` | `page` (`Page`), `pages`, `canonical_url` |
| `archive.html` | `all_posts`, `pages`, `canonical_url`, `pagination_page_urls` |
| `tag.html` | `tag` (display name), `safe_tag` (URL slug), `all_posts`, `pages`, `prev_page_url`, `next_page_url`, `canonical_url`, `pagination_page_urls` |
| `tags.html` | `tags` (dict of display name → post list), `pages`, `canonical_url` |
| `category.html` | `category`, `safe_category`, `all_posts`, `pages`, `prev_page_url`, `next_page_url`, `canonical_url`, `pagination_page_urls` |
| `categories.html` | `categories` (dict of display name → post list), `pages`, `canonical_url` |
| `search.html` | `pages`, `canonical_url` |
| `stats.html` | `stats` (`BlogStats`), `pages`, `canonical_url` |
| `calendar.html` | `calendar_years` (list of `CalendarYear`), `pages`, `canonical_url` |

## Post object

`Post` objects are passed to templates as items in `all_posts`, `prev_post`,
and `next_post`.

| Attribute | Type | Description |
|---|---|---|
| `title` | `str` | Post title. |
| `content` | `str` | Raw Markdown source. |
| `html_content` | `str` | Rendered HTML content. |
| `date` | `datetime \| None` | Publication date. |
| `category` | `str \| None` | Category name. |
| `tags` | `list[str] \| None` | Tag names. |
| `draft` | `bool` | `True` when the post is a draft. |
| `metadata` | `dict \| None` | Raw front matter dictionary. |
| `slug` | `str` (property) | URL slug derived from filename. |
| `url` | `str` (property) | URL path (e.g. `/2024/03/14/hello-world.html`). |
| `safe_category` | `str \| None` (property) | Category sanitised for use in URLs. |
| `description` | `str` (property) | Post description (from metadata or first paragraph). |
| `reading_time` | `int` (property) | Estimated reading time in minutes (minimum 1). |
| `modified_date` | `datetime \| None` (property) | Last-modified datetime from metadata, if set. |

Helper methods available on `Post`:

| Method | Returns | Description |
|---|---|---|
| `safe_tags()` | `list[str]` | Tags sanitised for URL use. |
| `sorted_tag_pairs()` | `list[tuple[str, str]]` | `(display, safe)` tag pairs sorted alphabetically. |

### Draft post visual indicator

When `post.draft` is `True`, the built-in templates automatically apply a
clear visual indicator to the post title wherever it is rendered:

- The post title is displayed in the **draft title colour** (`--draft-title-color`
  CSS custom property, default amber `#cc6600`).
- A **🚧 emoji** is appended after the title text.
- The containing `<article>` element receives the CSS class **`draft-post`**
  (for summary cards and individual post pages) or the link receives the class
  **`draft-title`** (in the date archive list).

This applies in every listing context (home page, tag pages, category pages,
date archive) as well as on the individual post page.  Non-draft posts are
never affected.

Custom templates that render `post.title` should replicate this pattern.  A
minimal implementation:

```html+jinja
<h2><a href="{{ post.url }}">{{ post.title }}{% if post.draft %} 🚧{% endif %}</a></h2>
```

To override the draft title colour, set `--draft-title-color` (and
`--dark-draft-title-color` for dark mode) in your custom stylesheet.  See
[Theming](theming.md) for the full CSS variable reference.

## Page object

`Page` objects represent static pages from the `pages/` directory.

| Attribute | Type | Description |
|---|---|---|
| `title` | `str` | Page title. |
| `content` | `str` | Raw Markdown source. |
| `html_content` | `str` | Rendered HTML content. |
| `metadata` | `dict \| None` | Raw front matter dictionary. |
| `slug` | `str` (property) | URL slug derived from filename. |
| `url` | `str` (property) | URL path (e.g. `/about.html`). |
| `description` | `str` (property) | Page description (from metadata or first paragraph). |

## Backlink object

`Backlink` objects are passed to `post.html` via the `backlinks` context variable
when `with_backlinks` is enabled.  Each entry represents one post that links
to the currently-displayed post.

| Attribute | Type | Description |
|---|---|---|
| `source_post` | `Post` | The post whose Markdown content contains the link. |
| `snippet` | `Markup` | HTML-safe excerpt from the source post surrounding the link, with up to 100 characters of context on each side and an ellipsis (`…`) where the excerpt is truncated.  The link text is wrapped in `<strong class="backlink-link-text">` so it stands out from the surrounding context. |

The `backlinks` list is always present in the `post.html` context (even when
`with_backlinks` is `false`) but will be empty when the feature is disabled or
when no other post links to the current post.

## BlogStats object

The `stats` context variable in `stats.html` is a `BlogStats` instance.  The
most template-relevant attributes are listed below.

| Attribute | Type | Description |
|---|---|---|
| `top_domains` | `list[tuple[str, int]]` | Top 20 externally-linked domains as `(domain, count)` pairs, sorted by count descending. |
| `top_internal_links` | `list[tuple[Post, int]]` | Top 20 posts by incoming internal link count as `(post, count)` pairs, sorted by count descending.  Only posts with at least one backlink are included.  Populated when `with_backlinks` is `true`; otherwise an empty list. |
| `longest_streaks` | `list[PostingStreak]` | Up to 10 longest consecutive posting streaks of 2 or more days. |
| `streak_variants` | `list[StreakChartVariant]` | Pre-computed streak chart variants (5, 9, and 10 trailing months). |

## Calendar objects

The `calendar.html` template receives a `calendar_years` variable containing a
list of `CalendarYear` objects in reverse chronological order.

### CalendarYear

| Attribute | Type | Description |
|---|---|---|
| `year` | `int` | The calendar year. |
| `year_url` | `str \| None` | URL to the yearly archive, or `None` when the year has no posts. |
| `has_posts` | `bool` | `True` when at least one post was published in this year. |
| `months` | `list[CalendarMonth]` | Months for this year in reverse chronological order (latest first). |

### CalendarMonth

| Attribute | Type | Description |
|---|---|---|
| `year` | `int` | The year this month belongs to. |
| `month` | `int` | The month number (1–12). |
| `month_name` | `str` | Full English month name (e.g. `"January"`). |
| `month_url` | `str \| None` | URL to the monthly archive, or `None` when the month has no posts. |
| `has_posts` | `bool` | `True` when at least one post was published in this month. |
| `weeks` | `list[list[CalendarDay]]` | Calendar grid rows, each containing exactly 7 `CalendarDay` entries in Monday-to-Sunday order. |

### CalendarDay

| Attribute | Type | Description |
|---|---|---|
| `date` | `datetime.date \| None` | The calendar date for this cell. `None` for padding slots that do not belong to the current month. |
| `post_count` | `int` | Number of posts published on this day (0 for non-post days and padding). |
| `day_url` | `str \| None` | URL to the daily archive. Set only when `post_count > 0`; `None` otherwise. |

## Template inheritance

All page templates extend `base.html`.  The inheritance chain is:

```
base.html
├── index.html
├── post.html
├── page.html
├── archive.html
├── tag.html
├── tags.html
├── category.html
├── categories.html
├── search.html
├── stats.html
└── calendar.html
```

Partial templates included by the above:

| Partial | Used by | Purpose |
|---|---|---|
| `_post_summary.html` | `index.html`, `tag.html`, `category.html`, `archive.html` | Renders one post summary card. |
| `_pagination.html` | `index.html`, `tag.html`, `category.html`, `archive.html` | Renders page navigation. |
| `_listing_meta_tags.html` | `index.html`, `tag.html`, `category.html`, `archive.html` | Renders `<meta>` tags for listing pages. |
| `meta_tags.html` | `post.html`, `page.html` | Renders Open Graph and SEO `<meta>` tags. |
| `_comment_invite.html` | `post.html` (via `comment_invite` block) | Renders the comment invitation section when `invite_comments` is enabled. |

### `_pagination.html` macro

The `pagination` macro in `_pagination.html` renders the numbered page navigation
widget.  It is called like this:

```jinja2
{% from '_pagination.html' import pagination %}
{{ pagination(page, total_pages, pagination_page_urls) }}
```

| Parameter | Type | Description |
|---|---|---|
| `page` | `int` | Current 1-based page number. |
| `total_pages` | `int` | Total number of pages. |
| `page_urls` | `list[str]` | Pre-computed list of page URLs (index 0 = page 1). Pass the `pagination_page_urls` context variable here. |

## Template blocks

`base.html` provides the following blocks that child templates can override:

| Block | Description |
|---|---|
| `title` | Content of the `<title>` element (defaults to `site_title`). |
| `feed_links` | `<link>` tags for RSS and Atom feeds. |
| `site_author_meta` | `<meta name="author">` tag. |
| `meta_tags` | For post/page-specific `<meta>` tags. |
| `extra_head` | Additional elements to inject into `<head>`. |
| `content` | Main page content (rendered inside `<main>`). |
| `feed_nav_links` | RSS and Atom links in the header navigation. |

`post.html` provides the following additional blocks:

| Block | Description |
|---|---|
| `backlinks` | The "References &amp; mentions" section shown after the bottom post-navigation on individual post pages when `with_backlinks` is enabled and there are inbound links.  Override this block in a custom `post.html` to change the layout or styling of the section. |
| `comment_invite` | The comment invitation section shown after the bottom post-navigation (and before the `backlinks` block) when `invite_comments` is enabled.  By default this block includes `_comment_invite.html`.  Override `_comment_invite.html` in your custom templates directory to change the wording or layout, or override this block entirely in a custom `post.html`. |

## CSS classes used by templates

The following CSS classes are part of the stable template/CSS contract:

| Class | Element | Purpose |
|---|---|---|
| `.site-container` | `div` | Outermost wrapper (flex row: sidebar + main). |
| `.sidebar` | `aside` | Fixed left sidebar. |
| `.sidebar-content` | `div` | Scrollable sidebar content. |
| `.sidebar-header` | `div` | Logo and title area. |
| `.sidebar-pages` | `div` | Navigation links from `pages/`. |
| `.sidebar-section` | `section` | A sidebar widget section (links, socials). |
| `.sidebar-links` | `ul` | List of sidebar links. |
| `.sidebar-socials` | `div` | Social icon links. |
| `.main-wrapper` | `div` | Content area (header + main + footer). |
| `.post-header` | `div` | Title, date, and metadata for a post page. |
| `.post-content` | `div` | Rendered post/page HTML body. |
| `.post-summary` | `article` | A single post card on a listing page. |
| `.post-navigation` | `nav` | Previous/next post links. |
| `.pagination` | `nav` | Page navigation on listing pages. |
| `.archive-post-count` | `span` | Parenthetical post count in archive headings (h1/h2/h3). |
| `.archive-toc-count` | `span` | Parenthetical numeric count in the archive TOC sidebar. |
| `.tag-cloud` | `div` | Tag cloud on the tags index page. |
| `.tags` | `div` | Inline tag badges on a post. |
| `.category-link` | `a` | Category badge link. |
| `.theme-toggle` | `button` | Dark/light mode toggle button. |
| `.highlight` | `div` | Syntax-highlighted code block. |
| `.backlinks` | `section` | "References &amp; mentions" container on a post page (only when `with_backlinks` is enabled and the post has inbound links). |
| `.backlinks-heading` | `h2` | Heading of the backlinks section. |
| `.backlinks-list` | `ul` | Ordered list of back-linking posts. |
| `.backlink-item` | `li` | A single back-link entry (one per referencing post). |
| `.backlink-meta` | `div` | Contains the source post's title link and date. |
| `.backlink-title` | `a` | Link to the source post's title. |
| `.backlink-date` | `time` | Publication date of the source post. |
| `.backlink-snippet` | `p` | Plain-text context snippet around the link. |
| `.backlink-link-text` | `strong` | The link text itself, highlighted within `.backlink-snippet` so it stands out from the surrounding italic context. |
| `.comment-invite` | `section` | Comment invitation container on a post page (only when `invite_comments` is enabled and an email address is configured). |
| `.comment-invite-content` | `p` | The invitation message paragraph. |
| `.comment-invite-link` | `a` | The `mailto:` link within the invitation message. |

## Stability policy

### What will not change in v2.x

- All context variable names listed in this document.
- All `Post` and `Page` attribute names listed in this document.
- All template block names listed in this document.
- The names and semantics of all CSS classes listed in this document.
- The `data-theme` attribute values (`"dark"` and `"light"`).
- The `--bg-color`, `--text-color`, and all other CSS custom properties listed
  in [Theming](theming.md).

### What may change

- The internal HTML structure of partial templates (elements inside
  `.post-summary`, `.pagination`, etc.) may evolve without a version bump,
  provided the outer class names and overall semantics are preserved.
- New context variables may be added to any template without notice.
- New CSS custom properties may be added at any time.
- Partial template names prefixed with `_` are considered internal and may
  be renamed in a minor release (though we will try to avoid this).

### Breaking change policy

A **breaking change** is any change that would require a user to update a
custom template or stylesheet to maintain the same behaviour.  Breaking
changes will:

1. Be labelled `BREAKING CHANGE` in [ChangeLog.md](changelog.md).
2. Include step-by-step migration instructions.
3. Only be introduced in a new **major** version (i.e. v2.x → v3.0), never
   in a minor or patch release.

Additive changes (new context variables, new CSS custom properties, new
template blocks) are backward-compatible and therefore require only a minor
version bump at most.
