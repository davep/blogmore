# Templates

BlogMore generates every page of your site using [Jinja2](https://jinja.palletsprojects.com/) templates. The default templates produce a clean, responsive design that works well for most blogs. If you need to change the look or layout of your site beyond what CSS can achieve, you can override the templates.

## The default templates

BlogMore ships with the following templates:

| Template | Purpose |
|---|---|
| `base.html` | The base layout, shared by all pages. Contains the `<head>`, sidebar, and main content area. |
| `index.html` | The blog's home page, showing a paginated listing of all posts. |
| `post.html` | An individual blog post. |
| `page.html` | A static page (from the `pages/` directory). |
| `archive.html` | The chronological archive of all posts. |
| `tag.html` | A listing of all posts with a particular tag. |
| `tags.html` | The full index of all tags used on the site. |
| `category.html` | A listing of all posts in a particular category. |
| `categories.html` | The full index of all categories on the site. |
| `search.html` | The client-side search page (only generated when `--with-search` is enabled). |
| `meta_tags.html` | A partial template included by `post.html` and `page.html` to render `<meta>` tags. |
| `_post_summary.html` | A partial template used by all listing pages (`index.html`, `tag.html`, `category.html`, `archive.html`) to render a single post summary article.  Edit this file to change how posts appear in every listing context at once. |
| `_listing_meta_tags.html` | A partial template used by listing pages to render the standard Open Graph and SEO `<meta>` tags.  Edit this file to change the meta tags for all listing pages at once. |
| `_pagination.html` | A partial template used by all listing pages to render page navigation. |
| `static/style.css` | The stylesheet for the entire site. |
| `static/theme.js` | JavaScript for the dark/light mode toggle and mobile sidebar. |
| `static/search.js` | JavaScript for the client-side search (only used when search is enabled). |

## Overriding templates

To customise the templates, copy the defaults from the BlogMore source code and place them in a directory of your choosing. You only need to copy the files you intend to modify — BlogMore will use your versions for any file it finds in your templates directory and fall back to its own defaults for everything else.

The default templates can be found in the BlogMore source tree at `src/blogmore/templates/`.

### Using a custom templates directory

Point BlogMore at your templates directory with `--templates`:

```bash
blogmore build posts/ --templates my-templates/
```

Or set it permanently in your [configuration file](configuration.md):

```yaml
templates: my-templates
```

### A simple example

Suppose you want to change the footer in the base template. Copy just `base.html` into your templates directory and edit it:

```
my-blog/
├── my-templates/
│   └── base.html       ← your customised version
├── posts/
│   └── hello-world.md
└── blogmore.yaml
```

```yaml
# blogmore.yaml
templates: my-templates
```

BlogMore will use your `base.html` and the built-in versions of all other templates.

### Adding extra stylesheets

For visual changes that don't require modifying the HTML structure, you can add a custom stylesheet rather than replacing `static/style.css`. This is often the simpler option for typography, colours, and spacing tweaks.

Place your CSS file in the `extras/` subdirectory of your content directory and add it to the `extra_stylesheets` list in your configuration:

```yaml
extra_stylesheets:
  - /custom.css
```

See the [Configuration Reference](configuration.md#extra_stylesheets) for details.
