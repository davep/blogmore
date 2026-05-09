# Linting Your Blog Content

BlogMore includes a built-in linter that checks your posts and pages for
common issues *before* you build the site.  Running `blogmore lint` is a
quick way to catch problems early — broken links, missing images, future
dates, and frontmatter errors — without generating any output files.

## What the linter checks

### Frontmatter errors

Any post or page whose YAML frontmatter cannot be parsed, or that is
missing a required field (such as `title`), is reported.  The linter
continues to check the remaining files even when some files fail to parse.

Common frontmatter problems include:

- Unquoted colons in a value (`title: My Post: The Sequel` is ambiguous
  YAML — quote the value instead: `title: "My Post: The Sequel"`).
- A missing `title` field (required for both posts and pages).
- An invalid value type, such as `tags: 42` where a list or string is
  expected.

### Broken internal links

The linter scans the Markdown content of every post and page for links that
point to internal URLs (root-relative paths like `/2024/01/01/my-post.html`
or full URLs that start with your `site_url`).  Each such link is checked
against the complete set of URLs that your posts and pages would produce.

The URL comparison accounts for your [`post_path`](configuration.md#post_path),
[`page_path`](configuration.md#page_path), and
[`clean_urls`](configuration.md#clean_urls) settings, so a link to
`/posts/my-post/` is recognised as valid when `clean_urls` is enabled and
the post maps to `posts/my-post/index.html`.

!!! note
    External links (those pointing to other domains) are **not** checked.
    Checking external links would be slow, unreliable, and privacy-invasive.

### Future dates

A `date` or `modified` frontmatter value that lies in the future (relative
to the current UTC time) is reported as a warning.  This often indicates a
typo — for example, writing `2025` when you meant `2024`.

### Missing image assets

Internal image links (`![alt](/path/to/image.png)`) are checked against the
`extras/` directory inside your content directory.  A link to
`/images/photo.jpg` is expected to correspond to the file
`<content_dir>/extras/images/photo.jpg`.  If the file is not found, the
linter reports it.

As with regular links, external image URLs (those starting with `http://` or
`https://`) are silently skipped.

## Running the linter

```bash
blogmore lint <content_dir>
```

Or using the `check` alias:

```bash
blogmore check <content_dir>
```

### Options

#### `content_dir` (positional, optional)

The directory containing your Markdown posts.  May be omitted when it is
specified in your `blogmore.yaml` configuration file.

#### `-c, --config <path>`

Path to a configuration file.  When omitted BlogMore searches for
`blogmore.yaml` or `blogmore.yml` in the current directory.  The
configuration file is used to read `post_path`, `page_path`, and
`clean_urls` so that URL comparisons match what the build would produce.

#### `--site-url <url>`

Base URL of the site (e.g. `https://example.com`).  When provided, full
URLs that start with this value are treated as internal links and checked.
Defaults to the empty string (no full-URL recognition).

#### `--include-drafts`

When specified, posts whose frontmatter contains `draft: true` are included
in the lint run.  By default, draft posts are skipped.

### Examples

Lint a content directory using settings from the default config file:

```bash
blogmore lint posts/
```

Lint with a specific config file and check drafts:

```bash
blogmore lint posts/ --config my-blog.yaml --include-drafts
```

Lint with a site URL so that self-referential full URLs are recognised as
internal links:

```bash
blogmore lint posts/ --site-url https://example.com
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | No issues found |
| `1`  | One or more issues were found (or a fatal error occurred) |

## Example output

When no issues are found:

```
Linting content in: posts/

No issues found. ✓
```

When issues are found:

```
Linting content in: posts/

[Frontmatter error] posts/2024-01-15-my-post.md
  Post 'tags' in frontmatter must be a string or list in: posts/2024-01-15-my-post.md
    Found: 42 (type: int)
    Fix: wrap the value in quotes or brackets, e.g. tags: 'my-tag' or tags: [tag1, tag2]

[Broken internal link] posts/2024-02-01-review.md
  Broken internal link '/2023/12/25/old-post.html' — no matching post or page found

[Future date] posts/2024-03-01-upcoming.md
  Post `date` is in the future: 2099-06-15 00:00:00

[Missing image] posts/2024-04-01-illustrated.md
  Internal image '/images/diagram.png' not found in extras/ directory

4 issues found.
```

## Using the linter in CI

Because `blogmore lint` returns a non-zero exit code when issues are found,
you can add it as a step in your CI pipeline before building:

```yaml
- name: Lint blog content
  run: blogmore lint posts/

- name: Build site
  run: blogmore build posts/
```

This catches broken links and other problems automatically on every push.
