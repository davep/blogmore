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

The linter currently performs the following checks:

### Malformed Frontmatter
It ensures that all posts and pages have valid YAML frontmatter. If a file cannot be parsed due to a syntax error in the frontmatter, it will be reported as an error.

### Broken Internal Links
The linter scans the generated HTML of your posts and pages and identifies any links that point to non-existent internal paths. This includes:
- Links to other posts or pages.
- Links to category and tag pages.
- Links to date-based archive pages.
- Links to special site pages (search, stats, calendar, etc.).
- Links to files in your `extras/` directory.

The linter takes your `clean_urls` setting and any custom path templates (`post_path`, `page_path`, etc.) into account when resolving links.

### Broken Image Links
Similar to internal links, the linter checks that all images used in your posts and pages resolve to valid internal paths or files in your `extras/` directory.

### Future Dates
The linter reports a warning if any post has a `date` or `modified` date set in the future. This helps you catch accidental future dates that might cause posts to not appear as expected.

### External Links
The linter does **not** check external links (links starting with `http://` or `https://` that point outside your site domain). This is to keep the linting process fast and avoid dependencies on an internet connection.

## Example Output

When errors are found, the linter will report them with the file path and line content (if applicable):

```text
Linting site in ./content...
ERROR: ./content/posts/my-post.md: Link points to non-existent internal path: /non-existent-page.html (resolved to /non-existent-page.html)
WARNING: ./content/posts/future-post.md: Post date is in the future: 2026-12-25 00:00:00
Linting complete: 1 error(s), 1 warning(s).
```

The `lint` command will exit with a non-zero status code if any errors are found, making it suitable for use in CI/CD pipelines.
