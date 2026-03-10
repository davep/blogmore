# Setting Up Your Blog

This guide walks you through setting up a new blog with BlogMore. It assumes you are comfortable working in a terminal, but explains each part of the structure in detail.

Before you begin, make sure BlogMore is installed. If it isn't, head to the [installation instructions](index.md#installation) first.

## Your working directory

Start by creating a top-level directory where your blog will live. This is where your content, configuration, and generated output will all sit together:

```bash
mkdir my-blog
cd my-blog
```

You can name this directory anything you like.

## The content directory

The content directory is where all of your Markdown files live. You can call it anything you like — `posts`, `content`, `blog`, `writing` — and point BlogMore at it when you run a command:

```bash
blogmore build posts/
```

Alternatively, you can set it once in a [configuration file](configuration.md) so you don't need to type it every time:

```yaml
content_dir: posts
```

See the [command line reference](command_line.md) for the full list of ways to specify the content directory.

### Organising your content

BlogMore scans the content directory recursively for `.md` files, so you can organise your posts however suits you best. None of these structures is better than another — choose whatever makes sense for you.

**Flat structure** — all posts in one directory:

```
posts/
├── hello-world.md
├── python-tips.md
└── web-development.md
```

**Organised by date**:

```
posts/
├── 2024/
│   ├── 01/
│   │   └── hello-world.md
│   └── 02/
│       └── python-tips.md
└── 2025/
    └── 01/
        └── web-development.md
```

**Organised by topic**:

```
posts/
├── python/
│   ├── decorators.md
│   └── type-hints.md
└── web/
    ├── css-grid.md
    └── javascript-tips.md
```

Whichever layout you choose, BlogMore determines post order using the `date` field in each post's [frontmatter](writing_a_post.md#frontmatter), not the directory structure.

### Date-prefixed filenames

If you'd like your filenames to reflect publication dates, BlogMore supports date-prefixed filenames such as `2026-02-18-hello-world.md`. The `YYYY-MM-DD-` prefix is automatically stripped from the generated URL slug, so the post will be accessible at a clean address. The post date still comes from the `date` field in frontmatter.

For more information on writing posts, see [Writing a Post](writing_a_post.md).

## The `extras` directory

Inside your content directory, you can create an `extras/` subdirectory for assets that should be copied straight into the output without any processing:

```
posts/
├── extras/
│   ├── robots.txt
│   ├── humans.txt
│   ├── icon.png
│   ├── custom.css
│   └── images/
│       ├── splash.png
│       └── thumbnails/
│           ├── tn1.jpeg
│           └── tn2.jpeg
└── hello-world.md
```

The contents are copied recursively to the root of the output directory, preserving the subdirectory structure. Using the example above, the output would contain:

```
robots.txt
humans.txt
icon.png
custom.css
images/splash.png
images/thumbnails/tn1.jpeg
images/thumbnails/tn2.jpeg
```

Common uses for `extras/` include:

- **Site icon** — a square, high-resolution PNG or JPEG image (ideally 1024×1024 or larger) that BlogMore uses to generate favicons and platform-specific icons automatically. See [Metadata and Sidebar — Site icons](metadata_and_sidebar.md#site-icons) for full details.
- **Custom stylesheets** — any CSS files you'd like included alongside the default styles.
- **Other assets** — fonts, images, or anything else that posts or pages link to directly.

## The `pages` directory

Inside your content directory you can also create a `pages/` subdirectory. Files here are treated as *static pages* rather than blog posts — they appear in the site navigation and are not included in the post listing, the archive, or the feeds:

```
posts/
├── pages/
│   ├── about.md
│   └── projects.md
└── hello-world.md
```

See [Writing a Page](writing_a_page.md) for details on what goes into a page and how pages differ from posts.

## The output directory

When you run `blogmore build`, the generated site is written to an `output/` directory by default:

```
my-blog/
├── posts/
│   └── hello-world.md
├── output/          ← generated site lives here
│   ├── index.html
│   └── ...
└── blogmore.yaml
```

You can change the output directory on the command line:

```bash
blogmore build posts/ --output public/
```

Or set it in your [configuration file](configuration.md):

```yaml
output: public
```

See the [command line reference](command_line.md) for all the options related to output.

## A minimal configuration file

Once you have your directory structure in place, it's worth creating a `blogmore.yaml` in your working directory so you don't have to pass the same arguments every time:

```yaml
content_dir: posts
output: public
site_title: "My Blog"
site_subtitle: "Thoughts on code and life"
site_url: "https://yourname.github.io/blog"
default_author: "Your Name"
```

With this in place, you can simply run:

```bash
blogmore build
blogmore serve
blogmore publish
```

For a full list of configuration options, see the [Configuration Reference](configuration.md).

## Next steps

Now that your blog is set up:

- [Writing a Post](writing_a_post.md) — learn how to write and format posts
- [Writing a Page](writing_a_page.md) — create static pages such as an about page
- [Metadata and Sidebar](metadata_and_sidebar.md) — configure your site's identity and appearance
- [Building and Publishing](building.md) — preview, build, and publish your site
- [Command Line Reference](command_line.md) — all commands and options
- [Configuration Reference](configuration.md) — all configuration file options
