"""Cover image generator for social media sharing using Pillow.

Provides programmatic generation of Open Graph (1200x630 px) sharing images
for posts based on metadata and configurable layout styles.
"""

import os
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFont

from blogmore.parser import Post
from blogmore.site_config import SiteConfig


def _wrap_text(text: str, font: Any, max_width: int) -> list[str]:
    """Wrap text to fit within a given maximum width in pixels.

    Args:
        text: The text to wrap.
        font: The Pillow font object to measure text with.
        max_width: The maximum width in pixels.

    Returns:
        A list of wrapped lines.
    """
    words = text.split()
    lines: list[str] = []
    current_line: list[str] = []

    for word in words:
        test_line = " ".join(current_line + [word]) if current_line else word
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _find_system_font(font_family: str, bold: bool = False) -> Path | None:
    """Find a system font file path matching the given family.

    Args:
        font_family: The font family name (e.g., 'Inter', 'Arial').
        bold: Whether to look for the bold variant.

    Returns:
        The Path to the font file if found, otherwise None.
    """
    search_dirs: list[Path] = []
    # OS-specific font directories
    if os.name == "nt":  # Windows
        windir = os.environ.get("WINDIR", "C:\\Windows")
        search_dirs.append(Path(windir) / "Fonts")
    else:  # macOS & Linux
        search_dirs.extend(
            [
                Path("/System/Library/Fonts"),
                Path("/Library/Fonts"),
                Path("/System/Library/Fonts/Supplemental"),
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path("~/.fonts").expanduser(),
                Path("~/.local/share/fonts").expanduser(),
            ]
        )

    # Clean the input font family name
    family_clean = font_family.lower().replace(" ", "")

    # Look for candidate names
    candidates: list[str] = []
    if bold:
        candidates.extend(
            [
                f"{family_clean}bd",
                f"{family_clean}-bold",
                f"{family_clean}_bold",
                f"{family_clean}bold",
                f"{family_clean}mtbold",
                f"{family_clean}mtbd",
            ]
        )
    else:
        candidates.extend(
            [
                family_clean,
                f"{family_clean}-regular",
                f"{family_clean}_regular",
                f"{family_clean}regular",
                f"{family_clean}mt",
            ]
        )

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for root, _, files in os.walk(s_dir):
            for file in files:
                f_path = Path(root) / file
                if f_path.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                    continue
                file_stem = f_path.stem.lower().replace(" ", "")
                for cand in candidates:
                    if file_stem == cand:
                        return f_path

    # Fallbacks for standard sans-serif
    fallbacks = ["arial", "helvetica", "dejavusans", "liberationsans", "segoeui"]
    for fallback in fallbacks:
        if bold:
            cand_fallbacks = [
                f"{fallback}bd",
                f"{fallback}-bold",
                f"{fallback}_bold",
                f"{fallback}bold",
                f"{fallback}mtbold",
                f"{fallback}mtbd",
            ]
        else:
            cand_fallbacks = [
                fallback,
                f"{fallback}-regular",
                f"{fallback}_regular",
                f"{fallback}regular",
                f"{fallback}mt",
            ]

        for s_dir in search_dirs:
            if not s_dir.exists():
                continue
            for root, _, files in os.walk(s_dir):
                for file in files:
                    f_path = Path(root) / file
                    if f_path.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                        continue
                    file_stem = f_path.stem.lower().replace(" ", "")
                    for c_fall in cand_fallbacks:
                        if file_stem == c_fall:
                            return f_path

    return None


def _get_font(font_family: str, size: int, bold: bool = False) -> Any:
    """Load a font object of the specified family and size.

    Args:
        font_family: The font family name.
        size: The font size in pixels.
        bold: Whether to load the bold variant.

    Returns:
        An ImageFont object.
    """
    # 1. Try to load directly (might be a system name PIL can resolve or direct path)
    try:
        return ImageFont.truetype(font_family, size)
    except OSError:
        pass

    # 2. Search OS directories
    font_path = _find_system_font(font_family, bold=bold)
    if font_path:
        try:
            return ImageFont.truetype(str(font_path), size)
        except OSError:
            pass

    # 3. Last resort fallback
    return ImageFont.load_default()


class CoverGenerator:
    """Generates social media sharing cover images for blog posts.

    Composes title, branding, and metadata using Pillow drawing context
    according to the selected layout template (minimalist, split, editorial).
    """

    def __init__(self, site_config: SiteConfig) -> None:
        """Initialize the cover image generator.

        Args:
            site_config: The blog's site configuration.
        """
        self.site_config = site_config
        self.config_block: dict[str, Any] = site_config.auto_covers

    def assign_cover_metadata(self, posts: list[Post]) -> None:
        """Assign the relative cover image path to eligible posts' metadata.

        Runs before HTML/page generation so templates can read the correct path.

        Args:
            posts: List of posts to process.
        """
        global_enabled = self.config_block.get("enabled", False)

        for post in posts:
            # Rule 1: Custom cover takes priority over auto cover.
            if post.metadata and post.metadata.get("cover"):
                continue

            # Determine layout choice
            auto_cover_val = post.metadata.get("auto_cover") if post.metadata else None

            if auto_cover_val is None:
                auto_cover = "default" if global_enabled else "none"
            else:
                auto_cover = str(auto_cover_val).strip().lower()

            if auto_cover == "none":
                continue

            # Calculate filename
            if self.site_config.content_dir:
                try:
                    rel_path = post.path.relative_to(self.site_config.content_dir)
                except ValueError:
                    rel_path = Path(post.path.name)
            else:
                rel_path = Path(post.path.name)

            rel_posix = rel_path.with_suffix("").as_posix()
            sanitized = re.sub(r"[^a-zA-Z0-9_\-/]", "_", rel_posix)
            filename = sanitized.replace("/", "-") + ".webp"

            if post.metadata is None:
                post.metadata = {}
            # Update post metadata to let templates pick it up
            post.metadata["cover"] = f"static/images/auto_covers/{filename}"

    def generate_covers(self, posts: list[Post]) -> None:
        """Render and save cover images to the output directory.

        Runs after the static assets have been deployed and cleared.

        Args:
            posts: List of posts to process.
        """
        global_enabled = self.config_block.get("enabled", False)
        target_dir = self.site_config.output_dir / "static" / "images" / "auto_covers"

        for post in posts:
            # Check if this post has a cover generated by us
            cover_path = post.metadata.get("cover") if post.metadata else None
            if not cover_path or not cover_path.startswith(
                "static/images/auto_covers/"
            ):
                continue

            # Extract filename from metadata
            filename = cover_path.split("static/images/auto_covers/")[-1]
            output_file = target_dir / filename

            # Determine layout choice
            auto_cover_val = post.metadata.get("auto_cover") if post.metadata else None

            if auto_cover_val is None:
                auto_cover = "default" if global_enabled else "none"
            else:
                auto_cover = str(auto_cover_val).strip().lower()

            # Fallback check
            if auto_cover == "none":
                continue

            # Determine actual layout template to use
            valid_layouts = {"minimalist", "split", "editorial"}
            if auto_cover == "default":
                layout = (
                    str(self.config_block.get("layout", "minimalist")).strip().lower()
                )
            else:
                layout = auto_cover

            if layout not in valid_layouts:
                layout = "minimalist"

            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)

            # Generate the image file
            self._render_cover_image(post, layout, output_file)

    def _render_cover_image(self, post: Post, layout: str, output_path: Path) -> None:
        """Render a single cover image to disk.

        Args:
            post: The post object to render.
            layout: The layout style name ('minimalist', 'split', 'editorial').
            output_path: The target output Path on disk.
        """
        # Canvas specification
        width, height = 1200, 630
        img = Image.new("RGB", (width, height), color="#0f172a")
        draw = ImageDraw.Draw(img)

        # Style tokens
        bg_type = self.config_block.get("background_type", "gradient")
        bg_color = self.config_block.get("background_color", "#0f172a")
        gradient_colors = self.config_block.get(
            "gradient_colors", ["#1e293b", "#0f172a"]
        )
        text_color_hex = self.config_block.get("text_color", "#f8fafc")
        meta_color_hex = self.config_block.get("meta_color", "#94a3b8")
        accent_color_hex = self.config_block.get("accent_color", "#38bdf8")
        font_family = self.config_block.get("font_family", "Inter")

        # Background rendering
        if bg_type == "gradient" and len(gradient_colors) >= 2:
            try:
                c1 = ImageColor.getrgb(gradient_colors[0])
                c2 = ImageColor.getrgb(gradient_colors[1])
                pixels = []
                for y in range(height):
                    ratio = y / (height - 1)
                    r = int(c1[0] + (c2[0] - c1[0]) * ratio)
                    g = int(c1[1] + (c2[1] - c1[1]) * ratio)
                    b = int(c1[2] + (c2[2] - c1[2]) * ratio)
                    pixels.append((r, g, b))
                grad_1d = Image.new("RGB", (1, height))
                grad_1d.putdata(pixels)
                gradient = grad_1d.resize((width, height), Image.Resampling.BILINEAR)
                img.paste(gradient, (0, 0))
            except ValueError:
                draw.rectangle([(0, 0), (width, height)], fill=bg_color)
        else:
            draw.rectangle([(0, 0), (width, height)], fill=bg_color)

        # Font sizing & loading
        font_title = _get_font(font_family, 60, bold=True)
        font_brand = _get_font(font_family, 28, bold=True)
        font_meta = _get_font(font_family, 24, bold=False)

        # Metadata parsing
        brand_name = self.site_config.site_title or "My Blog"
        date_str = ""
        if post.date and self.config_block.get("show_date", True):
            date_str = post.date.strftime("%b %d, %Y")

        read_time_str = ""
        if self.config_block.get("show_read_time", True):
            # Calculate reading time
            words = len(post.content.split()) if post.content else 0
            wpm = self.site_config.read_time_wpm or 200
            minutes = max(1, (words + wpm - 1) // wpm)
            read_time_str = f"{minutes} min read"

        author_str = ""
        if self.config_block.get("show_author", True):
            author_str = (
                (post.metadata.get("author") if post.metadata else None)
                or self.site_config.default_author
                or ""
            )

        # Join meta parts
        meta_parts = [p for p in (author_str, date_str, read_time_str) if p]
        meta_text = " • ".join(meta_parts)

        # Dispatch based on layout
        if layout == "split":
            self._draw_split_layout(
                draw,
                img,
                post,
                brand_name,
                meta_text,
                font_title,
                font_brand,
                font_meta,
                text_color_hex,
                meta_color_hex,
                accent_color_hex,
            )
        elif layout == "editorial":
            self._draw_editorial_layout(
                draw,
                post,
                brand_name,
                meta_text,
                font_title,
                font_brand,
                font_meta,
                text_color_hex,
                meta_color_hex,
                accent_color_hex,
            )
        else:
            self._draw_minimalist_layout(
                draw,
                post,
                brand_name,
                meta_text,
                font_title,
                font_brand,
                font_meta,
                text_color_hex,
                meta_color_hex,
                accent_color_hex,
            )

        img.save(output_path, "WEBP", lossless=True)

    def _draw_minimalist_layout(
        self,
        draw: ImageDraw.ImageDraw,
        post: Post,
        brand_name: str,
        meta_text: str,
        font_title: Any,
        font_brand: Any,
        font_meta: Any,
        text_color: str,
        meta_color: str,
        accent_color: str,
    ) -> None:
        """Draw minimalist center-aligned layout.

        Args:
            draw: The ImageDraw drawing context.
            post: The post being rendered.
            brand_name: The site brand name.
            meta_text: The joined metadata string.
            font_title: Font for the post title.
            font_brand: Font for site branding.
            font_meta: Font for metadata.
            text_color: Hex color for main text.
            meta_color: Hex color for metadata.
            accent_color: Hex color for accents/branding.
        """
        # Safe zone width is 1040 (1200 - 80 * 2)
        safe_width = 1040

        # Draw branding at top center
        if self.config_block.get("show_logo", True):
            brand_bbox = font_brand.getbbox(brand_name)
            brand_w = brand_bbox[2] - brand_bbox[0]
            draw.text(
                (600 - brand_w // 2, 80), brand_name, fill=accent_color, font=font_brand
            )

        # Title word wrap and drawing
        title_lines = _wrap_text(post.title, font_title, safe_width)
        # Limit to 3 lines max
        if len(title_lines) > 3:
            title_lines = title_lines[:3]
            title_lines[-1] = title_lines[-1] + "..."

        # Calculate heights
        line_heights = []
        for line in title_lines:
            bbox = font_title.getbbox(line)
            line_heights.append(bbox[3] - bbox[1])

        total_title_h = sum(line_heights) + (len(title_lines) - 1) * 15

        # Center title vertically
        y_cursor = 315 - total_title_h // 2

        for i, line in enumerate(title_lines):
            bbox = font_title.getbbox(line)
            w = bbox[2] - bbox[0]
            draw.text((600 - w // 2, y_cursor), line, fill=text_color, font=font_title)
            y_cursor += line_heights[i] + 15

        # Draw metadata at bottom center
        if meta_text:
            meta_bbox = font_meta.getbbox(meta_text)
            meta_w = meta_bbox[2] - meta_bbox[0]
            draw.text(
                (600 - meta_w // 2, 510), meta_text, fill=meta_color, font=font_meta
            )

    def _draw_split_layout(
        self,
        draw: ImageDraw.ImageDraw,
        img: Image.Image,
        post: Post,
        brand_name: str,
        meta_text: str,
        font_title: Any,
        font_brand: Any,
        font_meta: Any,
        text_color: str,
        meta_color: str,
        accent_color: str,
    ) -> None:
        """Draw split layout: left-aligned text, right-aligned graphic.

        Args:
            draw: The ImageDraw drawing context.
            img: The PIL Image canvas.
            post: The post being rendered.
            brand_name: The site brand name.
            meta_text: The joined metadata string.
            font_title: Font for the post title.
            font_brand: Font for site branding.
            font_meta: Font for metadata.
            text_color: Hex color for main text.
            meta_color: Hex color for metadata.
            accent_color: Hex color for accents/branding.
        """
        # Left section width = 720 px, margins = 80 px
        left_safe_width = 680

        # Draw branding at top-left
        if self.config_block.get("show_logo", True):
            draw.text((80, 80), brand_name, fill=accent_color, font=font_brand)

        # Title wrapping and drawing
        title_lines = _wrap_text(post.title, font_title, left_safe_width)
        if len(title_lines) > 4:
            title_lines = title_lines[:4]
            title_lines[-1] = title_lines[-1] + "..."

        line_heights = []
        for line in title_lines:
            bbox = font_title.getbbox(line)
            line_heights.append(bbox[3] - bbox[1])

        total_title_h = sum(line_heights) + (len(title_lines) - 1) * 15
        y_cursor = 315 - total_title_h // 2

        for i, line in enumerate(title_lines):
            draw.text((80, y_cursor), line, fill=text_color, font=font_title)
            y_cursor += line_heights[i] + 15

        # Draw metadata at bottom-left
        if meta_text:
            draw.text((80, 510), meta_text, fill=meta_color, font=font_meta)

        # Draw a decorative element on the right (35% width, x starts around 840)
        # Try loading the site logo from site_config and draw it resized on the right
        logo_path = self.site_config.sidebar_config.get("site_logo")
        logo_drawn = False
        if logo_path and self.site_config.content_dir:
            logo_clean = logo_path.split("#")[0].split("?")[0].lstrip("/")
            src_logo = self.site_config.content_dir / logo_clean
            if not src_logo.is_file():
                extras_logo = self.site_config.content_dir / "extras" / logo_clean
                if extras_logo.is_file():
                    src_logo = extras_logo

            if src_logo.is_file():
                try:
                    logo_img = Image.open(src_logo).convert("RGBA")
                    # Resize to fit within 240x240 box
                    logo_img.thumbnail((240, 240), Image.Resampling.LANCZOS)
                    logo_w, logo_h = logo_img.size
                    # Paste centered vertically on the right side (x_center = 980)
                    paste_x = 980 - logo_w // 2
                    paste_y = 315 - logo_h // 2
                    img.paste(logo_img, (paste_x, paste_y), mask=logo_img)
                    logo_drawn = True
                except Exception:
                    pass

        # Fallback decorative visual if no logo was drawn
        if not logo_drawn:
            # Draw a beautiful abstract geometric accent on the right
            draw.arc(
                [(900, 215), (1060, 375)], start=0, end=360, fill=accent_color, width=4
            )
            draw.arc(
                [(880, 195), (1080, 395)], start=0, end=360, fill=meta_color, width=2
            )
            draw.ellipse([(960, 275), (1000, 315)], fill=accent_color)

    def _draw_editorial_layout(
        self,
        draw: ImageDraw.ImageDraw,
        post: Post,
        brand_name: str,
        meta_text: str,
        font_title: Any,
        font_brand: Any,
        font_meta: Any,
        text_color: str,
        meta_color: str,
        accent_color: str,
    ) -> None:
        """Draw editorial layout: full-width asymmetric top-aligned card.

        Args:
            draw: The ImageDraw drawing context.
            post: The post being rendered.
            brand_name: The site brand name.
            meta_text: The joined metadata string.
            font_title: Font for the post title.
            font_brand: Font for site branding.
            font_meta: Font for metadata.
            text_color: Hex color for main text.
            meta_color: Hex color for metadata.
            accent_color: Hex color for accents/branding.
        """
        # Margins = 80 px, safe width = 1040 px
        safe_width = 1040

        # Draw Title top-left (y starts at 100)
        title_lines = _wrap_text(post.title, font_title, safe_width)
        if len(title_lines) > 3:
            title_lines = title_lines[:3]
            title_lines[-1] = title_lines[-1] + "..."

        y_cursor = 100
        line_heights = []
        for line in title_lines:
            bbox = font_title.getbbox(line)
            line_heights.append(bbox[3] - bbox[1])

        for i, line in enumerate(title_lines):
            draw.text((80, y_cursor), line, fill=text_color, font=font_title)
            y_cursor += line_heights[i] + 15

        # Excerpt or category pill if present below title
        category = post.category
        if category:
            cat_text = category.upper()
            cat_bbox = font_meta.getbbox(cat_text)
            cat_w = cat_bbox[2] - cat_bbox[0]
            cat_h = cat_bbox[3] - cat_bbox[1]

            pill_x1 = 80
            pill_y1 = y_cursor + 20
            pill_x2 = pill_x1 + cat_w + 30
            pill_y2 = pill_y1 + cat_h + 16

            # Draw pill background
            draw.rounded_rectangle(
                [(pill_x1, pill_y1), (pill_x2, pill_y2)],
                radius=8,
                fill=accent_color,
            )

            # Center coordinates of the pill with a visual offset correction
            cx = (pill_x1 + pill_x2) // 2
            cy = (pill_y1 + pill_y2) // 2 + 2

            # Contrast color for text inside pill, centered perfectly
            draw.text((cx, cy), cat_text, fill="#0f172a", font=font_meta, anchor="mm")

        # Draw a beautiful horizontal dividing line above footer
        draw.line([(80, 480), (1120, 480)], fill=meta_color, width=2)

        # Footer row: brand name on left, metadata on right
        footer_y = 510
        if self.config_block.get("show_logo", True):
            draw.text((80, footer_y), brand_name, fill=accent_color, font=font_brand)

        if meta_text:
            meta_bbox = font_meta.getbbox(meta_text)
            meta_w = meta_bbox[2] - meta_bbox[0]
            # Right-aligned footer meta
            draw.text(
                (1120 - meta_w, footer_y + 4),
                meta_text,
                fill=meta_color,
                font=font_meta,
            )
