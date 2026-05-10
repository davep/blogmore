# Linting

BlogMore includes a built-in linter to help you identify common issues in your blog posts and pages before you publish them. The linter checks for broken internal links, malformed frontmatter, and other potential problems.

## Using the Linter

You can run the linter using the `lint` command (or its alias `check`):

```bash
blogmore lint [content_dir]
```

Or:

```bash
blogmore check [content_dir]
```

If `content_dir` is not provided, BlogMore will use the directory specified in your configuration file or the current directory if it contains a `blogmore.yaml` file.

## What is Checked?

The linter categorizes its findings into **Errors** and **Warnings**.

### Errors

Errors represent critical issues that will likely result in a broken site or a failed build. The `lint` command will return a non-zero exit code if any errors are found.

*   **Malformed Frontmatter**: Ensures all posts and pages have valid YAML frontmatter. If a file cannot be parsed, it is reported as an error.
*   **Broken Internal Links**: Scans the generated HTML for links to non-existent internal paths (other posts, pages, categories, tags, archives, site features like search, or files in `extras/`).
*   **Broken Image Links**: Checks that all `<img>` sources resolve to valid internal paths or files in your `extras/` directory.
*   **Broken Cover Images**: Specifically verifies that the `cover` property in your post or page frontmatter points to a valid resource.
*   **Configuration Integrity**: Ensures your site configuration is healthy:
    *   Verifies that all page slugs listed in `sidebar_pages` actually exist.
    *   Checks that all internal-looking URLs in your `links:` and `socials:` configuration point to valid targets.

### Warnings

Warnings represent organizational or quality issues that won't break the build but might lead to a suboptimal blog experience. Warnings do **not** cause the `lint` command to fail.

*   **Missing Metadata**: Warns if a post is missing a **Title**, **Category**, **Tags**, or a **Date**.
*   **Future Dates**: Reports if a post's `date` or `modified` date is set in the future.
*   **Inconsistent Dates**: Flags cases where a post's `modified` date is earlier than its original publication `date`.
*   **Duplicate Titles**: Warns if two or more posts share the exact same title.
*   **Missing Alt Text**: Reports any inline images that are missing an `alt` attribute, or have an empty/whitespace-only `alt` attribute (e.g., `![]()`).
*   **Clean URL Suggestions**: If `clean_urls` is enabled, warns if internal links point explicitly to `index.html` (e.g., `[Home](/index.html)`) and suggests the cleaner alternative.
*   **Local Absolute Links**: Warns if internal links use the full `site_url` (e.g., `https://mysite.com/path/`) instead of a root-relative path (`/path/`). This improves content portability.
*   **External Links**: The linter does **not** check external links (starting with `http://` or `https://`) to ensure the process remains fast and offline-capable.

## Ignoring Specific Links

Sometimes you may have internal-looking links that are actually valid but point to resources not managed by BlogMore (for example, files handled by your web server or another application). You can tell the linter to ignore these links by adding them to your configuration file:

```yaml
linting:
  ignore:
    - /external-resource/
    - /dynamic-app/login.html
```

Any URL in this list will be treated by the linter as if it exists on disk, suppressing any "non-existent internal path" errors for that URL.

## Example Output

When issues are found, the linter will report them with the file path (relative to your content directory):

```text
Linting site in ./content...
ERROR: Sidebar (sidebar_pages) references non-existent page slug: broken-slug
ERROR: Sidebar links link points to non-existent internal path: /missing.html (resolved to /missing.html)
ERROR: posts/my-post.md: Link points to non-existent internal path: /non-existent-page.html (resolved to /non-existent-page.html)
ERROR: posts/welcome.md: Cover image points to non-existent internal path: /images/missing.png (resolved to /images/missing.png)
WARNING: posts/future-post.md: Post date is in the future: 2026-12-25 00:00:00
WARNING: posts/draft-post.md: Post has no category
WARNING: posts/duplicate-title-1.md: Duplicate post title 'Hello World' found in multiple files
WARNING: posts/image-post.md: Image is missing alt text: /attachments/logo.png
WARNING: posts/about.md: Link points to explicit 'index.html' while clean_urls is enabled: /index.html (consider using /)
WARNING: posts/contact.md: Link uses absolute URL for local site: https://mysite.com/contact/ (consider using root-relative link: /contact/)
Linting complete: 4 error(s), 5 warning(s).
```

The `lint` command will exit with a non-zero status code if any errors are found, making it suitable for use in CI/CD pipelines.
