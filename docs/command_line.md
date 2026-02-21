# Command Line Reference

This guide documents all BlogMore command-line options and commands.

## Basic Usage

```bash
blogmore <command> [arguments] [options]
```

## Commands

BlogMore provides three main commands:

- **`build`** - Generate the static site
- **`serve`** - Generate and serve the site locally with auto-reload
- **`publish`** - Build and publish the site to a git branch

### Command Aliases

Several commands have aliases for convenience:

- `build`, `generate`, `gen` - All equivalent
- `serve`, `test` - Both start the development server

## Global Options

### `--version`

Display the BlogMore version and exit.

```bash
blogmore --version
```

## Build Command

Generate a static site from Markdown posts.

### Synopsis

```bash
blogmore build <content_dir> [options]
blogmore generate <content_dir> [options]
blogmore gen <content_dir> [options]
```

### Arguments

**`content_dir`** (optional if specified in config file)
: Directory containing your Markdown blog posts. BlogMore scans this directory recursively for `.md` files.

```bash
blogmore build posts/
```

### Options

#### `-c, --config <path>`

Path to a YAML configuration file. If not specified, BlogMore automatically searches for `blogmore.yaml` or `blogmore.yml` in the current directory (`.yaml` takes precedence).

```bash
blogmore build posts/ --config custom-config.yaml
```

#### `-t, --templates <path>`

Directory containing custom Jinja2 templates. If not specified, uses the bundled default templates.

```bash
blogmore build posts/ --templates my-templates/
```

Custom templates should follow the structure of the default templates:
- `base.html`
- `index.html`
- `post.html`
- `archive.html`
- `tag.html`
- `category.html`
- `static/style.css`

#### `-o, --output <path>`

Output directory for the generated site. Default: `output/`

```bash
blogmore build posts/ --output public/
```

#### `--site-title <title>`

Title of your blog site. Default: `My Blog`

```bash
blogmore build posts/ --site-title "Dave's Blog"
```

#### `--site-subtitle <subtitle>`

Subtitle or tagline for your site. Optional.

```bash
blogmore build posts/ \
  --site-title "Dave's Blog" \
  --site-subtitle "Thoughts on Python and technology"
```

#### `--site-url <url>`

Base URL of your site. Used for generating absolute URLs in RSS/Atom feeds and canonical URLs. Optional but recommended.

```bash
blogmore build posts/ --site-url "https://davep.org/blog"
```

#### `--include-drafts`

Include posts marked with `draft: true` in frontmatter. By default, drafts are excluded.

```bash
blogmore build posts/ --include-drafts
```

#### `--clean-first`

Remove the output directory before generating the site. Useful to ensure no stale files remain.

```bash
blogmore build posts/ --clean-first
```

#### `--posts-per-feed <number>`

Maximum number of posts to include in RSS and Atom feeds. Default: `20`

```bash
blogmore build posts/ --posts-per-feed 50
```

#### `--default-author <name>`

Default author name for posts that don't specify an `author` field in frontmatter.

```bash
blogmore build posts/ --default-author "Dave Pearson"
```

#### `--extra-stylesheet <url>`

URL of an additional stylesheet to include. Can be an absolute URL or a path relative to your site root. This option can be used multiple times to include multiple stylesheets.

```bash
blogmore build posts/ \
  --extra-stylesheet "https://fonts.googleapis.com/css2?family=Inter" \
  --extra-stylesheet "/assets/custom.css"
```

#### `--icon-source <filename>`

Filename of the source icon image in the `extras/` directory. BlogMore will generate favicons and platform-specific icons from this image.

```bash
blogmore build posts/ --icon-source "my-logo.png"
```

If not specified, BlogMore auto-detects common icon filenames: `icon.png`, `icon.jpg`, `source-icon.png`, `app-icon.png`.

When a source icon is provided or detected, BlogMore generates 18 optimised icon files for iOS, Android, Windows, and standard favicons.

See [Using BlogMore - Adding Site Icons](using.md#adding-site-icons) for detailed usage.

#### `--with-search`

Enable client-side full-text search. When set, BlogMore generates a `search_index.json` file containing every post's title, URL, date, and plain-text content, and a `/search.html` page that performs in-browser search as the reader types. A **Search** link is also added to the navigation bar. No external services are required.

Search is **disabled by default**. Pass this flag to opt in.

```bash
blogmore build posts/ --with-search
```

When search is later disabled (flag omitted), any stale `search.html`, `search_index.json`, and `search.js` files from a previous build are automatically removed.

#### `--with-sitemap`

Generate an XML sitemap (`sitemap.xml`) in the root of the output directory. The sitemap conforms to the [Sitemaps protocol](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview) and includes an entry for every HTML page generated for the site, except `search.html`.

Sitemap generation is **disabled by default**. Pass this flag to opt in.

```bash
blogmore build posts/ --with-sitemap
```

A `--site-url` should be provided so that sitemap entries contain absolute URLs. If omitted, entries will fall back to `https://example.com`.

### Examples

Basic site generation:
```bash
blogmore build posts/
```

Generate with custom options:
```bash
blogmore build posts/ \
  --output public/ \
  --site-title "My Tech Blog" \
  --site-url "https://example.com" \
  --default-author "Jane Smith"
```

Clean build with drafts included:
```bash
blogmore build posts/ --clean-first --include-drafts
```

## Serve Command

Start a local development server that watches for changes and automatically rebuilds your site.

### Synopsis

```bash
blogmore serve [content_dir] [options]
blogmore test [content_dir] [options]
```

### Arguments

**`content_dir`** (optional)
: Directory containing Markdown posts. If provided, BlogMore will generate the site before serving. If omitted, serves an existing site from the output directory without regeneration.

```bash
# Generate and serve with auto-rebuild
blogmore serve posts/

# Serve an existing site without generation
blogmore serve
```

### Serve-Specific Options

#### `-p, --port <number>`

Port number for the local server. Default: `8000`

```bash
blogmore serve posts/ --port 3000
```

#### `--no-watch`

Disable watching for file changes. The site will be generated once (if `content_dir` is provided) but won't automatically rebuild on changes.

```bash
blogmore serve posts/ --no-watch
```

### Common Options

The serve command also accepts all the build command options:
- `-c, --config`
- `-t, --templates`
- `-o, --output`
- `--site-title`
- `--site-subtitle`
- `--site-url`
- `--include-drafts`
- `--clean-first`
- `--posts-per-feed`
- `--default-author`
- `--extra-stylesheet`
- `--icon-source`
- `--with-search`
- `--with-sitemap`

### Examples

Basic development server:
```bash
blogmore serve posts/
```

Custom port with drafts:
```bash
blogmore serve posts/ --port 3000 --include-drafts
```

Serve existing site without watching:
```bash
blogmore serve --output public/ --no-watch
```

Full configuration:
```bash
blogmore serve posts/ \
  --port 8080 \
  --output build/ \
  --site-title "Dev Blog" \
  --include-drafts
```

## Publish Command

Build your site and publish it to a git branch, typically for GitHub Pages.

### Synopsis

```bash
blogmore publish <content_dir> [options]
```

### Prerequisites

- You must be in a git repository
- Git must be installed and available in your PATH
- You should have a remote repository configured

### Arguments

**`content_dir`** (optional if specified in config file)
: Directory containing your Markdown blog posts.

```bash
blogmore publish posts/
```

### Publish-Specific Options

#### `--branch <branch-name>`

Git branch to publish to. Default: `gh-pages`

```bash
blogmore publish posts/ --branch main
```

#### `--remote <remote-name>`

Git remote to push to. Default: `origin`

```bash
blogmore publish posts/ --remote upstream
```

### Common Options

The publish command also accepts all the build command options:
- `-c, --config`
- `-t, --templates`
- `-o, --output`
- `--site-title`
- `--site-subtitle`
- `--site-url`
- `--include-drafts`
- `--clean-first`
- `--posts-per-feed`
- `--default-author`
- `--extra-stylesheet`
- `--icon-source`
- `--with-search`
- `--with-sitemap`

### How It Works

When you run `publish`, BlogMore:

1. Builds your site using the build command options
2. Verifies you're in a git repository
3. Creates a git worktree for the target branch in a temporary directory
4. Creates the branch if it doesn't exist
5. Clears the branch and copies your built site into it
6. Creates a `.nojekyll` file (required for GitHub Pages)
7. Commits the changes with a timestamp
8. Pushes to the specified remote

### Examples

Publish to GitHub Pages:
```bash
blogmore publish posts/ --branch gh-pages
```

Publish with custom configuration:
```bash
blogmore publish posts/ \
  --branch main \
  --site-url "https://example.com" \
  --clean-first
```

Publish to a different remote:
```bash
blogmore publish posts/ --remote upstream --branch pages
```

## Configuration File Priority

When both a configuration file and command-line options are present, command-line options always take precedence.

Example:
```yaml
# blogmore.yaml
site_title: "Config Title"
```

```bash
# Command-line overrides config file
blogmore build posts/ --site-title "CLI Title"
# Result: site_title will be "CLI Title"
```

## Path Expansion

All path arguments support tilde (`~`) expansion for home directory:

```bash
blogmore build ~/blog/posts/ --output ~/public_html/blog/
```

## Exit Codes

BlogMore uses standard exit codes:

- `0` - Success
- `1` - Error (with message printed to stderr)

## Environment Variables

BlogMore does not currently use environment variables for configuration. All configuration is done through command-line arguments or configuration files.

## Getting Help

Display help for BlogMore:
```bash
blogmore --help
```

Display help for a specific command:
```bash
blogmore build --help
blogmore serve --help
blogmore publish --help
```

## Common Workflows

### Daily Writing Workflow

```bash
# Start development server
blogmore serve posts/ --include-drafts

# Write and edit posts...
# Browser automatically refreshes on save

# When ready to publish
blogmore publish posts/
```

### Using Configuration Files

Create `blogmore.yaml`:
```yaml
content_dir: posts
output: public
site_title: "My Blog"
site_url: "https://example.com"
default_author: "Your Name"
```

Then use simplified commands:
```bash
blogmore build
blogmore serve
blogmore publish
```

### Multiple Sites

Use different config files for different sites:
```bash
blogmore build --config personal-blog.yaml
blogmore build --config work-blog.yaml
```

## See Also

- [Configuration](configuration.md) - Detailed configuration file documentation
- [Getting Started](getting_started.md) - Tutorial for creating your first blog
