# Metadata and Sidebar

A BlogMore site is more than just a collection of posts. This page explains how to configure your site's identity — its title, description, and URL — as well as the sidebar, which can include a logo, custom links, and social media icons.

All of the settings discussed here can be set via the [command line](command_line.md) or in your [configuration file](configuration.md). The configuration file is recommended for anything you want to persist between commands.

## Site metadata

### Site title

The name of your blog, shown in the sidebar header and in the browser tab.

```yaml
site_title: "Dave's Tech Blog"
```

Command line: `--site-title "Dave's Tech Blog"`

Default: `My Blog`

### Site subtitle

An optional tagline displayed below the site title in the sidebar.

```yaml
site_subtitle: "Python, web development, and open source"
```

Command line: `--site-subtitle "Python, web development, and open source"`

### Site URL

The base URL of your site. This is used to construct absolute URLs in RSS and Atom feeds, canonical link tags, and Open Graph tags. Include the protocol (`https://`) but no trailing slash.

```yaml
site_url: "https://davep.org/blog"
```

Command line: `--site-url "https://davep.org/blog"`

Setting this correctly is important if you intend to publish feeds or share posts on social media.

### Site description

A fallback description for pages that don't have one of their own (index pages, archive pages, tag and category pages, and posts whose content doesn't begin with a text paragraph).

```yaml
site_description: "A blog about Python, web development, and open source software"
```

Individual posts and pages whose frontmatter contains a `description` field, or whose content starts with a paragraph, use that content-specific description instead.

### Site keywords

Default keywords for the `<meta name="keywords">` tag, applied to pages that don't have more specific keywords. Individual posts use their tags as keywords, so `site_keywords` only comes into play for listing pages and posts with no tags.

```yaml
site_keywords: "blog, technology, programming, python"
```

You can also write this as a YAML list:

```yaml
site_keywords:
  - blog
  - technology
  - programming
  - python
```

### Default author

The author name to use for posts that don't specify an `author` field in their frontmatter.

```yaml
default_author: "Dave Pearson"
```

Command line: `--default-author "Dave Pearson"`

## Site logo

You can display a logo image at the top of the sidebar by setting `site_logo` to a URL or path:

```yaml
site_logo: /images/logo.png
```

The image is displayed above the site title. It can be hosted externally:

```yaml
site_logo: https://example.com/images/logo.svg
```

## Site icons

BlogMore can automatically generate a full set of favicons and platform-specific icons from a single source image. This means you only need to prepare one image and BlogMore takes care of the rest.

### Preparing your source image

Place a square, high-resolution image — ideally 1024×1024 pixels or larger — in the `extras/` subdirectory of your content directory:

```
posts/
└── extras/
    └── icon.png
```

BlogMore will detect it automatically if the filename is one of:

- `icon.png` *(recommended)*
- `icon.jpg` or `icon.jpeg`
- `source-icon.png`
- `app-icon.png`

If you use a different filename, tell BlogMore via the configuration file:

```yaml
icon_source: "my-logo.png"
```

Or on the command line:

```bash
blogmore build posts/ --icon-source my-logo.png
```

**Requirements:**

- Format: PNG or JPEG
- Size: Square, ideally 1024×1024 or larger
- Transparency: PNG with a transparent background works best for icons that need to sit on different coloured backgrounds

### What gets generated

When a source icon is detected, BlogMore generates 18 icon files in the `/icons` subdirectory of your output:

```
output/
└── icons/
    ├── favicon.ico                    (16×16, 32×32, 48×48 multi-resolution)
    ├── favicon-16x16.png
    ├── favicon-32x32.png
    ├── favicon-96x96.png
    ├── apple-touch-icon.png           (180×180)
    ├── apple-touch-icon-120.png       (120×120)
    ├── apple-touch-icon-152.png       (152×152)
    ├── apple-touch-icon-167.png       (167×167)
    ├── apple-touch-icon-precomposed.png
    ├── android-chrome-192x192.png
    ├── android-chrome-512x512.png
    ├── mstile-70x70.png
    ├── mstile-144x144.png
    ├── mstile-150x150.png
    ├── mstile-310x310.png
    ├── mstile-310x150.png
    ├── site.webmanifest               (PWA manifest)
    └── browserconfig.xml              (Windows tile configuration)
```

The necessary HTML `<link>` and `<meta>` tags are added to every page automatically, but only when the icons actually exist. There is nothing to configure beyond providing the source image.

## Sidebar configuration

### Custom links

Add custom navigation links to the sidebar. Each entry has a `title` and a `url`:

```yaml
links:
  - title: About
    url: /about.html
  - title: Projects
    url: /projects.html
  - title: Contact
    url: /contact.html
```

Links can point to pages on your site or to external URLs:

```yaml
links:
  - title: My Main Site
    url: https://example.com
  - title: GitHub Profile
    url: https://github.com/username
```

These links appear in the sidebar below any pages from your `pages/` directory.

### Social media icons

Add social media links to the sidebar as icons. Each entry has a `site` (the platform name) and a `url`:

```yaml
socials:
  - site: github
    url: https://github.com/davep
  - site: mastodon
    url: https://fosstodon.org/@davep
  - site: bluesky
    url: https://bsky.app/profile/davep.org
```

The `site` value maps directly to a [Font Awesome brand icon](https://fontawesome.com/icons?d=gallery&s=brands) name. Any Font Awesome brand icon name works, including:

`github`, `mastodon`, `bluesky`, `twitter`, `threads`, `linkedin`, `youtube`, `instagram`, `facebook`, `lastfm`, `steam`, and many more.

To change the section title from the default "Social", use `socials_title`:

```yaml
socials_title: "Connect"
socials:
  - site: github
    url: https://github.com/davep
```

The same can be set from the command line with `--socials-title`.

## See also

- [Command Line Reference](command_line.md) — all command-line options
- [Configuration Reference](configuration.md) — all configuration file options
