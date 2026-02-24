# BlogMore ChangeLog

## Unreleased

- Added optional JavaScript minification via the `--minify-js` command-line
  switch or the `minify_js: true` configuration option.
  ([#166](https://github.com/davep/blogmore/pull/166))
- Updated `blogmore.yaml.example` to include all available configuration
  options (`with_sitemap`, `minify_css`, `minify_js`).
  ([#168](https://github.com/davep/blogmore/pull/168))

## v0.13.0

**Released: 2026-02-23**

- FontAwesome loading is now non-blocking: `font-display` changed from
  `block` to `swap`, and a `<link rel="preload">` hint for the WOFF2 font
  file is added to all pages that use FontAwesome icons, improving initial
  page rendering speed. ([#163](https://github.com/davep/blogmore/pull/163))

## v0.12.0

**Released: 2026-02-23**

- Removed redundant CSS rules from `style.css`.
  ([#159](https://github.com/davep/blogmore/pull/159))
- The default `og:image` for the site index page now uses the `icon_source`
  generated platform icon (`android-chrome-512x512.png`) when available,
  falling back to `site_logo` if no platform icons have been generated.
  Post and page templates that don't have an explicit `cover` image set now
  also default to the platform icon for `og:image` and `twitter:image`.
  ([#160](https://github.com/davep/blogmore/pull/160))
- Added optional CSS minification via the `--minify-css` command-line switch
  or the `minify_css: true` configuration option.
  ([#161](https://github.com/davep/blogmore/pull/161))

## v0.11.0

**Released: 2026-02-22**

- Added the `site_description` configuration option. When set, it is used as
  a fallback description for any `head` metadata that uses a description of
  the page. ([#146](https://github.com/davep/blogmore/pull/146))
- Added the `site_keywords` configuration option. When set, it is used as a
  a fallback set of keywords for any `head` metadata that uses them.
  ([#150](https://github.com/davep/blogmore/pull/150))
- Author metadata is now added to the `head` of all pages, if the site's
  default author has been set.
  ([#152](https://github.com/davep/blogmore/pull/152))
- Added `og:title` meta tag to all generated pages that previously lacked it
  (index, archive, tag, category, tags overview, categories overview, and
  search pages). The title is derived from the site name, subtitle, and a
  description of the page type.
  ([#153](https://github.com/davep/blogmore/pull/153))
- Added full social/share-friendly `<head>` meta tags to the main index page,
  including `og:type`, `og:url`, `og:site_name`, `og:image`, `twitter:card`,
  `twitter:title`, and `twitter:image`. The image is taken from the configured
  site logo, or the largest generated platform icon if no logo is set.
  ([#154](https://github.com/davep/blogmore/pull/154))
- Added automatic FontAwesome CSS optimisation. This reduces the FontAwesome
  CSS overhead down to only what's needed for the "social icons" in the
  sidebar, rather than pulling down the whole FontAwesome CSS.
  ([#155](https://github.com/davep/blogmore/pull/155))

## v0.10.0

**Released: 2026-02-22**

- Fixed admonitions merging multiple paragraphs into one.
  ([#135](https://github.com/davep/blogmore/pull/135))
- Fixed `article:modified_time` meta tag not using ISO 8601 format when a
  `modified` frontmatter value is set.
  ([#138](https://github.com/davep/blogmore/pull/138))
- When icons are generated, a copy of `favicon.ico` is now also placed in
  the root of the output for backward compatibility. A `shortcut icon` link
  header is also included for legacy browser support.
  ([#140](https://github.com/davep/blogmore/pull/140))

## v0.9.0

**Released: 2026-02-21**

- Added optional XML sitemap generation.
  ([#127](https://github.com/davep/blogmore/pull/127))
- Fixed posts not being discovered recursively (Copilot documented that this
  was a feature, but never actually implemented it).
  ([#130](https://github.com/davep/blogmore/pull/130))
- Fixed the top-level navigation menu overflowing the viewport on
  narrow/mobile screens.
  ([#131](https://github.com/davep/blogmore/pull/131))

## v0.8.0

**Released: 2026-02-20**

- Footnotes are now rendered in a slightly smaller font size to visually
  differentiate them from body text.
  ([#121](https://github.com/davep/blogmore/pull/121))
- Post date timestamps are now formatted as `YYYY-MM-DD HH:MM:SS TZ` and
  each component (year, month, day) links to its corresponding archive page.
  ([#123](https://github.com/davep/blogmore/pull/123))
- Added optional client-side full-text search across post titles and
  content. Search is off by default.
  ([#124](https://github.com/davep/blogmore/pull/124))

## v0.7.0

**Released: 2026-02-20**

- Fixed `serve` mode failing with `FileNotFoundError` when `clean_first` is
  enabled. ([#118](https://github.com/davep/blogmore/pull/118))

## v0.6.0

**Released: 2026-02-19**

- Fixed duplicate HTML element IDs when multiple posts with footnotes appear
  on the same index page.
  ([#114](https://github.com/davep/blogmore/pull/114))
- Improved table styling with subtle borders, a distinct header background,
  and alternating row shading that works in both light and dark modes.
  ([#115](https://github.com/davep/blogmore/pull/115))

## v0.5.0

**Released: 2026-02-19**

- Fixed relative URLs in RSS/Atom feed entry content being left as
  root-relative paths; they are now rewritten to absolute URLs using the
  configured site URL, resolving feed-validator warnings.
  ([#110](https://github.com/davep/blogmore/pull/110))

## v0.4.0

**Released: 2026-02-19**

- Added auto-generation of various 'favicon' types from a single source
  image. ([#103](https://github.com/davep/blogmore/pull/103))

## v0.3.0

**Released: 2026-02-18**

- Initial public release.

[//]: # (ChangeLog.md ends here)
