# BlogMore ChangeLog

## Unreleased

**Released: WiP**

- Added optional XML sitemap generation.
  ([#127](https://github.com/davep/blogmore/pull/127))
- Fixed posts not being discovered recursively (Copilot documented that this
  was a feature, but never actually implemented it).
  ([#130](https://github.com/davep/blogmore/pull/130))
- Fixed the top-level navigation menu overflowing the viewport on narrow/mobile
  screens by allowing nav items to wrap to the next line.
  ([#132](https://github.com/davep/blogmore/pull/132))

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
