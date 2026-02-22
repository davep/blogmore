"""FontAwesome CSS optimization for blogmore.

Generates a minimal FontAwesome CSS file containing only the brand icons
actually used in the site configuration, reducing CSS payload from ~80KB to
~2-5KB.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# FontAwesome version targeted by this optimizer
FONTAWESOME_VERSION = "6.5.1"

# Full CDN stylesheet URL (fallback when optimization fails)
FONTAWESOME_CDN_CSS_URL = (
    f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome"
    f"/{FONTAWESOME_VERSION}/css/all.min.css"
)

# CDN integrity hash for the full stylesheet
FONTAWESOME_CDN_CSS_INTEGRITY = (
    "sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13"
    "TZye+giMm8e2LwA=="
)

# GitHub raw URL for FontAwesome icon metadata
FONTAWESOME_METADATA_URL = (
    f"https://raw.githubusercontent.com/FortAwesome/Font-Awesome"
    f"/{FONTAWESOME_VERSION}/metadata/icons.json"
)

# CDN base URL for FontAwesome web font files
FONTAWESOME_CDN_WEBFONTS_BASE = (
    f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome"
    f"/{FONTAWESOME_VERSION}/webfonts"
)

# Local path (relative to site root) where the optimized CSS is written
FONTAWESOME_LOCAL_CSS_PATH = "/static/fontawesome.css"


class FontAwesomeOptimizer:
    """Generate optimized FontAwesome CSS containing only needed brand icons.

    Fetches the official FontAwesome icon metadata from GitHub to obtain the
    Unicode codepoints for each requested icon, then assembles a minimal CSS
    file containing only the ``@font-face`` declaration, the base
    ``.fa-brands`` / ``.fab`` rules, and the individual icon definitions.

    Fonts themselves remain on the CDN so browsers can cache them across
    sites.
    """

    def __init__(self, icon_names: list[str]) -> None:
        """Initialize the optimizer with the set of icons to include.

        Args:
            icon_names: List of FontAwesome brand icon names (e.g.
                ``["github", "mastodon"]``).
        """
        self.icon_names = icon_names

    def fetch_icon_metadata(self) -> dict[str, Any]:
        """Fetch FontAwesome icon metadata from GitHub.

        Returns:
            Dictionary mapping icon name to its metadata (including the
            ``unicode`` codepoint field).

        Raises:
            urllib.error.URLError: If the metadata cannot be fetched from
                GitHub.
            ValueError: If the response cannot be parsed as JSON.
        """
        with urllib.request.urlopen(FONTAWESOME_METADATA_URL) as response:
            return dict(json.loads(response.read().decode("utf-8")))

    def build_css(self, metadata: dict[str, Any]) -> str:
        """Build a minimal CSS string for only the requested brand icons.

        Args:
            metadata: FontAwesome icon metadata as returned by
                :meth:`fetch_icon_metadata`.

        Returns:
            CSS string containing the ``@font-face`` declaration, base class
            rules, and one ``::before`` rule per requested icon found in the
            metadata.
        """
        woff2_url = f"{FONTAWESOME_CDN_WEBFONTS_BASE}/fa-brands-400.woff2"
        ttf_url = f"{FONTAWESOME_CDN_WEBFONTS_BASE}/fa-brands-400.ttf"

        lines: list[str] = [
            "@font-face {",
            '    font-family: "Font Awesome 6 Brands";',
            "    font-style: normal;",
            "    font-weight: 400;",
            "    font-display: block;",
            f'    src: url("{woff2_url}") format("woff2"),',
            f'         url("{ttf_url}") format("truetype");',
            "}",
            "",
            ".fa-brands,",
            ".fab {",
            '    font-family: "Font Awesome 6 Brands";',
            "    font-style: normal;",
            "    font-weight: 400;",
            "    font-variant: normal;",
            "    text-rendering: auto;",
            "    line-height: 1;",
            "    -webkit-font-smoothing: antialiased;",
            "    -moz-osx-font-smoothing: grayscale;",
            "    display: var(--fa-display, inline-block);",
            "}",
            "",
        ]

        for icon_name in self.icon_names:
            icon_data = metadata.get(icon_name)
            if icon_data is None:
                continue
            codepoint = icon_data.get("unicode", "")
            if codepoint:
                lines.append(
                    f'.fa-{icon_name}::before {{ content: "\\{codepoint}"; }}'
                )

        return "\n".join(lines) + "\n"

    def generate(self, output_dir: Path) -> bool:
        """Fetch metadata, build CSS, and write it to the output directory.

        The CSS file is written to ``output_dir/static/fontawesome.css``.

        Args:
            output_dir: Root output directory of the generated site.

        Returns:
            ``True`` if the optimized CSS file was written successfully,
            ``False`` if the metadata could not be fetched (caller should
            fall back to the CDN stylesheet).
        """
        try:
            metadata = self.fetch_icon_metadata()
        except (urllib.error.URLError, ValueError, OSError) as error:
            print(f"Warning: Could not fetch FontAwesome metadata: {error}")
            return False

        css_content = self.build_css(metadata)

        static_dir = output_dir / "static"
        static_dir.mkdir(parents=True, exist_ok=True)

        css_path = static_dir / "fontawesome.css"
        css_path.write_text(css_content, encoding="utf-8")

        return True
