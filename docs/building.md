# Building and Publishing

Once you have some posts written, you'll want to preview your site locally, build it for production, and eventually publish it. This page covers all three.

## Previewing with `serve`

The `serve` command builds your site and starts a local HTTP server. It also watches your content directory for changes and automatically rebuilds the site whenever you save a file, so you can see your edits reflected in the browser almost immediately.

```bash
blogmore serve posts/
```

Once the server is running, open `http://localhost:8000` in your browser to preview your site.

### Changing the port

If port 8000 is already in use, specify a different one with `--port`:

```bash
blogmore serve posts/ --port 3000
```

### Disabling auto-rebuild

If you'd prefer the site not to rebuild automatically when files change, use `--no-watch`:

```bash
blogmore serve posts/ --no-watch
```

### Serving an existing build

You can also serve an already-built site without regenerating it by omitting the content directory:

```bash
blogmore serve --output public/
```

### Including drafts

During development you'll often want to preview posts you've marked as drafts. Pass `--include-drafts` to include them:

```bash
blogmore serve posts/ --include-drafts
```

See [Writing a Post — draft](writing_a_post.md#draft) for how to mark a post as a draft.

### Testing your custom 404 page

If you have a [`404.md`](writing_a_page.md#the-special-case-of-404md) in your `pages/` directory, the development server will serve it automatically for any URL that doesn't exist, so you can verify it looks right before publishing.

## Building

The `build` command generates your complete static site and writes it to the output directory:

```bash
blogmore build posts/
```

By default, the generated site is written to `output/`. You can change this with `--output`:

```bash
blogmore build posts/ --output public/
```

### Clean builds

To make sure no files from a previous build linger in the output directory, use `--clean-first`. This removes the output directory before generating the site:

```bash
blogmore build posts/ --clean-first
```

This is particularly useful in automated pipelines or when you've removed or renamed posts.

### Optional features

#### Client-side search

Pass `--with-search` to generate a full-text search index and a `/search.html` page. The search runs entirely in the browser; no external service is required. A **Search** link is added to the site navigation automatically.

```bash
blogmore build posts/ --with-search
```

#### XML sitemap

Pass `--with-sitemap` to generate a `sitemap.xml` in the root of the output directory, covering every HTML page on the site (except `search.html`). Set `site_url` for the sitemap entries to contain absolute URLs.

```bash
blogmore build posts/ --with-sitemap --site-url "https://example.com"
```

#### Minification

To reduce file sizes delivered to visitors, you can minify the generated CSS and JavaScript:

```bash
blogmore build posts/ --minify-css --minify-js
```

When minification is enabled, `style.css` becomes `styles.min.css` and `theme.js` becomes `theme.min.js`.

### Using a configuration file

If you have a `blogmore.yaml` in your working directory, you can run `blogmore build` without any arguments and it will pick up all the settings from the file:

```bash
blogmore build
```

See the [Configuration Reference](configuration.md) for all available options.

## Publishing

The `publish` command builds your site and pushes it to a git branch, making it ready to serve from GitHub Pages or any similar git-backed hosting service.

### Prerequisites

Before publishing you will need:

1. Your blog directory to be a git repository (or inside one)
2. A remote repository configured (e.g. on GitHub)
3. Git installed and available in your `PATH`

### Publishing to GitHub Pages

Commit any outstanding changes to your source repository first:

```bash
git add .
git commit -m "Add new blog posts"
```

Then publish:

```bash
blogmore publish posts/ --branch gh-pages --remote origin
```

This command will:

1. Build your site
2. Create a git worktree for the target branch in a temporary directory
3. Create the branch if it doesn't already exist
4. Clear the branch and copy the built site into it
5. Create a `.nojekyll` file (required for GitHub Pages to serve the site correctly)
6. Commit the changes with a timestamp
7. Push to the specified remote

### Configuring GitHub Pages

After your first publish, go to your repository on GitHub and set up Pages:

1. Click **Settings** → **Pages**
2. Under "Source", select the `gh-pages` branch
3. Click **Save**

Your site will be available at `https://username.github.io/repository-name/` within a few minutes.

For more details, see the [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

### Publishing to other branches

You can publish to any branch by changing `--branch`:

```bash
blogmore publish posts/ --branch main --remote origin
```

### Using a configuration file

With a `blogmore.yaml` in place, you can simplify the publish command to:

```bash
blogmore publish
```

A typical production configuration:

```yaml
content_dir: posts
output: public
site_url: "https://example.com"
clean_first: true
branch: gh-pages
remote: origin
```

See the [Configuration Reference](configuration.md) for all publish-related options, and the [Command Line Reference](command_line.md) for a full list of flags.
