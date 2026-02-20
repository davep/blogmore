# BlogMore ChangeLog

## Unreleased

**Released: WiP**

- Footnotes are now rendered in a slightly smaller font size to visually
  differentiate them from body text.
  ([#121](https://github.com/davep/blogmore/pull/121))

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
